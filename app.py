import random

import gevent
from gevent import monkey
monkey.patch_all()
import datetime
import hashlib
from flask import Flask, session, request, redirect, url_for, render_template, flash
from flask_socketio import emit, join_room,SocketIO,leave_room, Namespace
import os
import query
from geng import gengenerateID

user_dict1= {}

app = Flask(__name__)   #定义模块名字为APP
app.config.update({     #配置APP模块
    'DEBUG':True,
    'TEMPLATES_AUTO_RELOAD' :True,
    'SECRET_KEY': os.urandom(10)
})
socketio = SocketIO(cors_allowed_origins="*") #防止出问题
socketio.init_app(app)   #创建socket实例
user_dict = {}
basedir = os.path.abspath(os.path.dirname(__file__))
def getLoginDetails():    #获取用户登录状态
    if 'email' not in session:
        loggedIn = False
        userName = 'please sign in'
        print(2)
    else:
        print(1)
        loggedIn = True
        sql = "SELECT user_name FROM chatroom.users WHERE email = %s"
        params = [session['email']]
        userName = query.query(sql,params)
        session['user'] = userName[0][0]
    return (loggedIn, userName[0][0])


#判断账户密码是否匹配
def is_valid(email, password):
    sql = 'SELECT email, password FROM chatroom.users'
    data =query.query_no(sql)
    for row in data:
        if row[0] == email and row[1] == hashlib.md5(password.encode()).hexdigest():
            return True
    return False


def create_uuid():  # 生成唯一的图片的名称字符串，防止图片显示时的重名问题
    nowTime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")  # 生成当前时间
    randomNum = random.randint(0, 100)  # 生成的随机整数n，其中0<=n<=100
    if randomNum <= 10:
        randomNum = str(0) + str(randomNum)
    uniqueNum = str(nowTime) + str(randomNum)
    return uniqueNum
#登录
@app.route("/", methods = ['POST', 'GET'])
@app.route("/login", methods = ['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        print(email)
        print(password)
        user_socket = request.environ.get('wsgi.websocket')
        user_dict[email] = user_socket
        if is_valid(email, str(password)):
            session['email'] = email
            flash('登录成功')
            print('yes')
            return redirect(url_for('index'))
        else:
            error = 'Invalid UserId / Password'
            print('no1')
            flash('登录失败')
            return render_template('login.html', error=error)
    else:
        flash('登录失败')
        return render_template('login.html')

@app.route("/logout")
def logout():
    session.pop('email', None)
    return redirect(url_for('login'))


@app.route("/register", methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        #Parse form data
        password = request.form['password']
        email = request.form['email']
        name = request.form['name']
        if is_valid(email, password):
            flash('账号已存在，请登录')
            return render_template("login.html")
        else:
            # Ino = gengenerateID()
            # sql = "select * from Issue where Ino = '%s'" % Ino
            # params=[Ino]
            # result=query.query(sql,params)
            # 如果result不为空，即存在该ID，就一直生成128位随机ID,直到不重复位置
            # while result is not None:
            #     Ino = gengenerateID()
            #     sql = "select * from Issue where Ino = '%s'" % Ino
            #     params = [Ino]
            #     result = query.query(sql, params)
            sql = 'INSERT INTO chatroom.users (email,password,user_name,avatar_url) VALUES (%s,%s,%s,%s)'
            params = [email,hashlib.md5(password.encode()).hexdigest(),name,'/static/images/001.jpg']
            msg = query.update(sql,params)
            if msg == 'Changed successfully':
                flash('注册成功')
                return render_template("login.html")
            else:
                flash('注册失败')
                return render_template('register.html')
    else:
        return render_template('register.html')


@app.route("/index", methods = ['POST', 'GET'])
def index():
    if 'email' not in session:
        return redirect(url_for('login'))
    else:
        loggedIn, userName = getLoginDetails()
        sql = "SELECT avatar_url FROM chatroom.users WHERE email = %s"#获取头像
        params = [session['email']]
        avatar_url = query.query(sql, params)
        sql = "SELECT user_name,users.avatar_url,users.email,users.user_id FROM chatroom.users" #获取用户名
        users = query.query_no(sql)
        sql = "SELECT user_id FROM chatroom.users WHERE email = %s"  # 获取头像
        params = [session['email']]
        id1 = query.query(sql, params)
        print(id1)
        return render_template("index.html",userName = userName,avatar_url=avatar_url[0][0],users = users,id1=id1[0][0])

@app.route("/chatroom", methods = ['POST', 'GET'])
def chatroom():
    if 'email' not in session:
        return redirect(url_for('login'))
    else:
        loggedIn, userName = getLoginDetails()
        sql = "SELECT messages.content,messages.create_time,users.user_name,users.avatar_url,messages.user_id,messages.photo FROM chatroom.messages,chatroom.users where messages.user_id = users.user_id and messages.chatroom_name='chatroom' order by messages.create_time"
        message = query.query_no(sql)
        sql = "SELECT user_name,users.avatar_url FROM chatroom.users"
        users = query.query_no(sql)
        sql = "SELECT avatar_url FROM chatroom.users WHERE email = %s"
        params = [session['email']]
        avatar_url = query.query(sql, params)
        return render_template("chatroom.html",userName = userName,message = message,users = users,avatar_url = avatar_url)

# 私聊
@app.route("/private/<Ino>", methods = ['POST', 'GET'])
def private(Ino):
    if 'email' not in session:
        return redirect(url_for('login'))
    else:
        t=str(Ino).split('-')
        print(t)
        Ino='/private/'+Ino
        loggedIn, userName = getLoginDetails()
        sql = "SELECT messages.content,messages.create_time,users.user_name,users.avatar_url,messages.user_id,messages.photo FROM chatroom.messages,chatroom.users where messages.user_id = users.user_id and messages.chatroom_name='%s' order by messages.create_time" % Ino
        message = query.query_no(sql)
        sql = "SELECT user_name,users.avatar_url FROM chatroom.users WHERE user_id='%s' or user_id='%s'" % (t[0],t[1])
        users = query.query_no(sql)
        print(users)
        sql = "SELECT avatar_url FROM chatroom.users WHERE email = %s"
        params = [session['email']]
        avatar_url = query.query(sql, params)
        return render_template("profile.html",userName = userName,message = message,users = users,avatar_url = avatar_url,)





#连接主页
@socketio.on('Iconnect', namespace='/index')
def Iconnect():
    print('连接主页成功')

#接收更换的头像的路径
@socketio.on('avatar_url' ,namespace='/index')
def avatar_url(information):
    email = session['email']
    avatar_url = information.get('avatar_url')
    avatar_url = "/"+avatar_url.split("/", 3)[-1]
    sql = "UPDATE chatroom.users SET avatar_url = %s WHERE email = %s "
    params = [avatar_url,email]
    msg = query.update(sql, params)
    print(msg)

class MyCustomNamespace(Namespace):
    def on_connect(self):
        print('连接成功')

    def on_joined(self,information):
        # 'joined'路由是传入一个room_name,给该websocket连接分配房间,返回一个'status'路由
        room_name = information
        user_name = session.get('user')
        print(information)
        print("加入房间成功")
        join_room(room_name)
        user_dict1[user_name] = room_name
        print(user_dict1)
        emit('status', {'server_to_client': user_name + ' enter the room'}, room=room_name)

    def on_leave(self,information):
        room_name = information
        user_name = session.get('user')
        print(information)
        print("退出房间成功")
        leave_room(room_name)
        user_dict1.pop(user_name)
        print(user_dict1)
        emit('status', {'server_to_client': user_name + ' leave the room'}, room=room_name)

    def on_text(self,information):
        print('接受成功1')
        text = information.get('text')
        user_name = session.get('user')  # 获取用户名称
        chatroom_name = information.get('chatroom')
        photo=information.get('photo')
        file_path=""
        if photo:
            print("接收到了图片")
            file_path = "/static/images/" + create_uuid() + '.jpg'
            with open(basedir+file_path, 'wb+') as f:
                f.write(photo)
        sql = "SELECT user_id FROM chatroom.users WHERE email = %s"
        params = [session['email']]
        print(params)
        user_id = query.query(sql, params)[0]  # 获取用户ID
        print(user_id)
        create_time = datetime.datetime.now()
        create_time = datetime.datetime.strftime(create_time, '%Y-%m-%d %H:%M:%S')
        sql = 'INSERT INTO chatroom.messages (chatroom_name,content,user_id,create_time,photo) VALUES (%s,%s,%s,%s,%s)'
        params = [chatroom_name, text, user_id, create_time, file_path]
        query.update(sql, params)  # 将聊天信息插入数据库，更新数据库
        sql = "SELECT avatar_url FROM chatroom.users WHERE email = %s"
        params = [session['email']]
        avatar_url = query.query(sql, params)  # 获取用户头像
        # 返回聊天信息给前端
        emit('message', {
            'user_name': user_name,
            'text': text,
            'create_time': create_time,
            'photo': file_path,
            'avatar_url': avatar_url,
        }, broadcast=True)
socketio.on_namespace(MyCustomNamespace('/chatroom'))

if __name__ == '__main__':
    #app.run(debug=True, use_reloader=False)
    socketio.run(app)
