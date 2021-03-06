#!/usr/bin/python

import web
import status
import util
import bcrypt
import uuid

urls = (
  '/', 'HouseList',
  '/house/?', 'HouseList',
  '/house/([0-9]+)/?', 'HouseDetail',
  '/room/([0-9]+)/?', 'RoomDetail',
  '/([a-zA-Z_.]+)/?', 'Static'
)

from HTMLParser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

class HouseList(object):
  def GET(self):
    houses = util.select('houses')
    raise status.ApiReturn('templates/house_list', houses)

class HouseDetail(object):
  def GET(self, hid):
    house = util.select_one('houses', where='id=$hid', vars={'hid': hid})
    hcom = util.select('house_com', where='house_id=$hid',  vars={'hid': hid})
    rooms = util.select('rooms', where='house_id=$hid',  vars={'hid': hid}, order='room_no ASC')
    
    raise status.ApiReturn('templates/house_detail', house, list(hcom), list(rooms))
  
  def POST(self,hid):
    var = web.data()
    util.insert('house_com', com=strip_tags(var), house_id=hid)

class RoomDetail(object):
  def GET(self, rid):
    room = util.select_one('rooms', where='id=$rid',  vars={'rid': rid})
    house = util.select_one('houses', where='id=$hid',  vars={'hid': room.house_id})
    coms = util.select('room_com', where='room_id=$rid',  vars={'rid': rid})
    
    raise status.ApiReturn('templates/room_detail', house, room, list(coms)) 
  
  def POST(self,rid):
    var = web.data()
    util.insert('room_com', com=strip_tags(var), room_id=rid)

class Static(object):
  def GET(self,page):
    raise status.ApiReturn('static/' + page)



'''

class RealQPage(object):
  def GET(self,q):
    sess = util.get_sess()
    raise status.ApiReturn('static/question', q, sess)

class QList(object):
  def GET(self):
    params = web.input(limit=20, offset=0)
    res2 = util.select('qlist JOIN users ON qlist.uid = users.id', what='qlist.id AS id, users.name AS name, qlist.opt1 AS opt1, qlist.opt2 AS opt2', limit=params.limit, order='qlist.id DESC', offset=params.offset)
    res = [r for r in res2]
    if len(res) < 1 and params.offset>0:
      raise status.ApiError('403 Invalid Page')
    raise status.ApiReturn('templates/qlist', res)
  
  def POST(self):
    sess = util.get_sess()
    if not sess:
      raise status.ApiError('401 Unauthorized')
    qx = web.input()
    
    try:
      util.insert('qlist', uid=sess.uid, opt1=qx.opt1, opt2=qx.opt2)
    except AttributeError:
      raise status.ApiError('401 Missing Input(s)')
    
    raise status.ApiError('200 OK')

class QPage(object):
  def GET(self, pid):
    params = web.input(limit=20, offset=0)
    
    qx = util.select_one('qlist JOIN users ON qlist.uid = users.id', where='qlist.id=$id', vars={'id': pid})
    if qx is None:
      raise status.ApiError('401 Invalid Question')
    res2 = util.select('alist JOIN qlist ON qlist.id = alist.qid JOIN users ON qlist.uid = users.id', where='qid=$id', limit=params.limit, offset=params.offset, order='alist.id DESC', vars={'id': pid})
    res = [r for r in res2]
    if len(res) < 1 and params.offset>0:
      raise status.ApiError('403 Invalid Page')
    
    sess = util.get_sess()
    raise status.ApiReturn('templates/question', qx, res)
  
  def POST(self, pid):
    qx = util.select_one('qlist', where='id=$id', vars={'id': pid})
    if qx is None:
      raise status.ApiError('401 Invalid Question')
    sess = util.get_sess()
    
    data = web.data()
    util.insert('alist', ans=data, up=0, down=0, qid=qx.id)
    
    raise status.ApiError('200 OK')
    

class Register(object):
  def GET(self):
    raise status.ApiReturn('templates/register')
    
  def POST(self):
    var = web.input()
    
    if 'fb' in var:
      raise status.ApiError('200 OK')
    try:
      if var.pword != var.repword:
        raise status.ApiError('403 Field Mismatch')
      hpword = bcrypt.hashpw(var.pword, bcrypt.gensalt())
      res = util.insert('users', email=var.email, pword=hpword, name=var.name)
      
      sess = str(uuid.uuid4())[:64]
      values = {
        'sess': sess,
        'uid': res
      }
      util.insert('sessions', **values)
      web.setcookie('wsid_login', sess, expires=86400, path='/')
    except KeyError as err:
      raise status.ApiError('401 Unauthorized')
      
    raise status.ApiError('200 OK')

class Logout(object):
  def POST(self):
    try:
      sess_key = web.cookies().wsid_login
      sess = util.select_one('sessions', where='sess=$s', vars={'s': sess_key})
      web.setcookie('wsid_login',sess_key,expires=-1)
      print "del", util.delete('sessions', where='sess=$s', vars={'s': sess_key})
    except AttributeError:
      raise status.ApiError('401 Not logged in')
    except KeyError:
      raise status.ApiError('401 Invalid session')
    raise status.ApiError('200 OK')

class Login(object):
  def GET(self):
    xsrf = str(uuid.uuid1())
    util.insert('xsrf', token=xsrf)
    raise status.ApiReturn('templates/login', xsrf)
  
  def user_auth(self, email, pword):
    user = util.select_one('users', where='email=$e', vars={'e':email})
    if user is None:
      return None
    hashed = user.pword
    if bcrypt.hashpw(pword, hashed) == hashed:
      return user
    return None
    
  def POST(self):
    var = web.input()
    
    
    if 'fb' in var:
      xsrf = util.select_one('xsrf', where='token=$tok', vars={'tok': var.xsrf})
      if xsrf is None:
        raise status.ApiError('401 Unauthorized')
      
    try:
      xsrf = util.select_one('xsrf', where='token=$tok', vars={'tok': var.xsrf})
      if xsrf is None:
        raise status.ApiError('401 Unauthorized')
      
      user = self.user_auth(var.email, var.pword)
      if user is None:
        print "this one"
        raise status.ApiError('401 Unauthorized')
      
      sess = str(uuid.uuid4())[:64]
      values = {
        'sess': sess,
        'uid': user['id']
      }
      util.insert('sessions', **values)
      web.setcookie('wsid_login', sess, path='/')
    except AttributeError as err:
      print "that one"
      raise status.ApiError('401 Unauthorized (%s)' % err)
      
    web.redirect('/')
    #raise status.ApiError('200 OK')
'''

if __name__ == "__main__":
  app = web.application(urls, globals())
  app.internalerror = web.debugerror
  app.run()
