from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS  # Add this import
from engineio.payload import Payload

Payload.max_decode_packets = 200

app = Flask(__name__)
app.config['SECRET_KEY'] = "thisismys3cr3tk3y"

CORS(app)  # Add this line to handle CORS

socketio = SocketIO(app)

_users_in_room = {}
_room_of_sid = {}
_name_of_sid = {}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        room_id = request.form['room_id']
        return redirect(url_for("entry_checkpoint", room_id=room_id))
    return render_template("home.html")

@app.route("/room/<string:room_id>/")
def enter_room(room_id):
    if room_id not in session:
        return redirect(url_for("entry_checkpoint", room_id=room_id))
    return render_template("chatroom.html", room_id=room_id, display_name=session[room_id]["name"], mute_audio=session[room_id]["mute_audio"], mute_video=session[room_id]["mute_video"])

@app.route("/room/<string:room_id>/checkpoint/", methods=["GET", "POST"])
def entry_checkpoint(room_id):
    if request.method == "POST":
        display_name = request.form['display_name']
        mute_audio = request.form['mute_audio']
        mute_video = request.form['mute_video']
        session[room_id] = {"name": display_name, "mute_audio": mute_audio, "mute_video": mute_video}
        return redirect(url_for("enter_room", room_id=room_id))
    return render_template("chatroom_checkpoint.html", room_id=room_id)

@socketio.on("connect")
def on_connect():
    sid = request.sid
    print(f"New socket connected {sid}")

@socketio.on("join-room")
def on_join_room(data):
    sid = request.sid
    room_id = data["room_id"]
    display_name = session[room_id]["name"]
    
    join_room(room_id)
    _room_of_sid[sid] = room_id
    _name_of_sid[sid] = display_name
    
    print(f"[{room_id}] New member joined: {display_name}<{sid}>")
    emit("user-connect", {"sid": sid, "name": display_name}, broadcast=True, include_self=False, room=room_id)
    
    if room_id not in _users_in_room:
        _users_in_room[room_id] = [sid]
        emit("user-list", {"my_id": sid})
    else:
        usrlist = {u_id: _name_of_sid[u_id] for u_id in _users_in_room[room_id]}
        emit("user-list", {"list": usrlist, "my_id": sid})
        _users_in_room[room_id].append(sid)

    print("\nusers: ", _users_in_room, "\n")

@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    room_id = _room_of_sid[sid]
    display_name = _name_of_sid[sid]

    print(f"[{room_id}] Member left: {display_name}<{sid}>")
    emit("user-disconnect", {"sid": sid}, broadcast=True, include_self=False, room=room_id)

    _users_in_room[room_id].remove(sid)
    if len(_users_in_room[room_id]) == 0:
        _users_in_room.pop(room_id)

    _room_of_sid.pop(sid)
    _name_of_sid.pop(sid)

    print("\nusers: ", _users_in_room, "\n")

@socketio.on("data")
def on_data(data):
    sender_sid = data['sender_id']
    target_sid = data['target_id']
    if sender_sid != request.sid:
        print(f'[Not supposed to happen!] request.sid and sender_id don\'t match!!!')

    if data["type"] != "new-ice-candidate":
        print(f'{data["type"]} message from {sender_sid} to {target_sid}')
    socketio.emit('data', data, room=target_sid)

if __name__ == "__main__":
    socketio.run(app, debug=True)
