import random
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

players = {}
history = []
orphan = None


def check_field(field):
    ships = [0, 0, 0, 0]
    for y in range(10):
        for x in range(10):
            if field[y][x] != ' ':
                continue
            if x > 0 and y > 0 and field[y - 1][x - 1] == ' ':
                return None
            if x < 9 and y > 0 and field[y - 1][x + 1] == ' ':
                return None
            if x > 0 and field[y][x - 1] == ' ':
                continue
            if y > 0 and field[y - 1][x] == ' ':
                continue
            x2 = x + 1
            while x2 < 10 and field[y][x2] == ' ':
                x2 += 1
            y2 = y + 1
            while y2 < 10 and field[y2][x] == ' ':
                y2 += 1
            size = max(x2 - x, y2 - y)
            if size > 4:
                return None
            ships[size - 1] += 1
    return ships


def draw_field(field, show_ships):
    lines = ['    A  B  C  D  E  F  G  H  I  J  ',
             '  +------------------------------+']
    for y in range(len(field)):
        p = lines[len(lines) - 1]
        if y + 1 < 10:
            t = ' ' + str(y + 1) + '| .  .  .  .  .  .  .  .  .  . |'
            n = '  |                              |'
        else:
            t = '10| .  .  .  .  .  .  .  .  .  . |'
            n = '  +------------------------------+'
        for x in range(len(field[y])):
            cx = 4 + 3 * x
            if show_ships:
                if field[y][x] in (' ', 'X'):
                    if y > 0 and field[y - 1][x] in (' ', 'X'):
                        p = p[:cx - 2] + '|   |' + p[cx + 3:]
                    else:
                        p = p[:cx - 2] + '+---+' + p[cx + 3:]
                    if y < 9 and field[y + 1][x] in (' ', 'X'):
                        n = n[:cx - 2] + '|   |' + n[cx + 3:]
                    else:
                        n = n[:cx - 2] + '+---+' + n[cx + 3:]
                    t = t[:cx - 2] + '| ' + field[y][x] + ' |' + t[cx + 3:]
                    if x > 0 and field[y][x - 1] in (' ', 'X'):
                        p = p[:cx - 2] + '-' + p[cx - 1:]
                        t = t[:cx - 2] + ' ' + t[cx - 1:]
                        n = n[:cx - 2] + '-' + n[cx - 1:]
                    if x < 9 and field[y][x + 1] in (' ', 'X'):
                        p = p[:cx + 2] + '-' + p[cx + 3:]
                        t = t[:cx + 2] + ' ' + t[cx + 3:]
                        n = n[:cx + 2] + '-' + n[cx + 3:]
            if field[y][x] in ('X', 'O'):
                t = t[:cx] + field[y][x] + t[cx + 1:]
        lines = lines[:len(lines) - 1] + [p, t, n]
    return lines


def parse_coords(coords):
    if coords is None or len(coords) < 2:
        return None
    c = ' '
    if coords[0] == '-':
        c = '.'
        coords = coords[1:]
    x = coords[0]
    if x in 'ABCDEFGHIJ':
        x = ord(x) - ord('A')
    elif x in 'abcdefghij':
        x = ord(x) - ord('a')
    else:
        return None
    try:
        y = int(coords[1:]) - 1
    except ValueError:
        y = -1
    if y < 0 or y > 9:
        return None
    return x, y, c


class RequestHandler(BaseHTTPRequestHandler):
    def sendResponse(self, body):
        self.send_response(200, 'OK')
        self.send_header('Content/type', 'text/html')
        self.end_headers()
        response = '<html>' \
                   '<head></head><body>' \
                   f'<div style="text-align: center">{body}</div>' \
                   '</body>' \
                   '</html>'
        self.wfile.write(bytes(response, 'utf-8'))

    def do_GET(self):
        request = self.path.split('?', 1)
        path = request[0]
        args = {}
        if len(request) > 1:
            for t in request[1].split('&'):
                p = t.split('=', 1)
                args[p[0]] = urllib.parse.unquote(p[1])

        if path != '/':
            self.send_error(404, 'Not found')
            return

        global players
        global history
        player = None
        uid = args.get('uid')
        if uid is not None:
            player = players.get(uid)

        if player is None:
            name = args.get('name')
            if name is None:
                response = '<p>Welcome to Sea Battleships game!'
                if len(history) > 0:
                    response += '<p>Previous matches:<br>'
                    for winner in history:
                        response += f"{winner['name']} won over {winner['opponent']['name']}<br>"
                response += '<p><script>' \
                            'function keyPress(event) {' \
                            ' if (event.key == "Enter")' \
                            '  sendName();' \
                            '}' \
                            'function sendName() {' \
                            ' window.location.replace(window.location.pathname +' \
                            ' "?name=" + document.getElementById("name").value);' \
                            '}</script>' \
                            '<label for="name">Enter your name: </label> ' \
                            '<input type="text" onkeypress="keyPress(event)" name="name" id="name" autofocus/> ' \
                            '<button onclick="sendName()">Enter</button>'
                self.sendResponse(response)
                return

            uid = str(random.getrandbits(64))
            player = {'uid': uid, 'name': name, 'state': 'place'}
            field = ['..........']
            for i in range(1, 10):
                field.append(field[0])
            player['field'] = field
            players[uid] = player
            global orphan
            if orphan is not None:
                orphan['opponent'] = player
                player['opponent'] = orphan
                orphan = None
            else:
                orphan = player

        if player['state'] == 'place':
            pos = args.get('pos')
            if args.get('remove') is not None:
                if pos is not None:
                    pos = '-' + pos
            pos = parse_coords(pos)
            field = player['field']
            if pos is not None:
                old_line = field[pos[1]]
                new_line = old_line[:pos[0]] + pos[2] + old_line[pos[0] + 1:]
                field[pos[1]] = new_line

                ships = check_field(field)
                if ships is None:
                    field[pos[1]] = old_line
            ships = check_field(field)

            response = f"<p>Hello {player['name']}!\n"
            if player.get('opponent') is None:
                response += "<p>While waiting for an opponent, place your ships.\n"
            else:
                response += f"<p>Your opponent is {player['opponent']['name']}, place your ships.\n"
            response += '<pre>'
            response += '\n'.join(draw_field(player['field'], True))
            response += '</pre>' \
                        '<p>'
            comma = ''
            if ships[3] != 1:
                response += '1 four cell'
                comma = ', '
            if ships[2] != 2:
                response += comma + '2 triple cell'
                comma = ', '
            if ships[1] != 3:
                response += comma + '3 double cell'
                comma = ', '
            if ships[0] != 4:
                response += comma + '4 single cell'
                comma = ', '
            if comma != '':
                response += ' ships to be placed.' \
                            '<p><script>' \
                            'function keyPress(event) {' \
                            ' if (event.key == "Enter")' \
                            '  sendPos(true);' \
                            '}' \
                            'function sendPos(add) {' \
                            ' window.location.replace(window.location.pathname +' \
                            f' "?uid={uid}&pos=" + (add ? "" : "-") + document.getElementById("pos").value);' \
                            '}</script>' \
                            '<label for="pos">Enter coordinates </label> ' \
                            '<input type="text" onkeypress="keyPress(event)" name="pos" id="pos" size=4 ' \
                            'oninput="this.value = this.value.toUpperCase()" autofocus/> ' \
                            '<label> to </label> ' \
                            '<button onclick="sendPos(true)">Add</button>' \
                            '<label> or </label> ' \
                            '<button onclick="sendPos(false)">Remove</button>' \
                            '<label>cells.</label> '
                self.sendResponse(response)
                return
            else:
                player['state'] = 'ready'

        if player['state'] == 'ready':
            response = f"<p>Hello {player['name']}!\n"
            if player.get('opponent') is None:
                response += '<p>Waiting for an opponent to join.\n'
                response += '<pre>'
                response += '\n'.join(draw_field(player['field'], True))
                response += '</pre>'
                response += '<p>Please stand by...\n' \
                            '<script>' \
                            'setTimeout(function() {' \
                            ' window.location.replace(' \
                            f' window.location.pathname + "?uid={uid}"); ' \
                            '}, 2000);</script>'
                self.sendResponse(response)
                return
            elif player['opponent']['state'] == 'place':
                response += f"<p>Your opponent is {player['opponent']['name']}.\n"
                response += '<pre>'
                response += '\n'.join(draw_field(player['field'], True))
                response += '</pre>'
                response += f"<p>Waiting for {player['opponent']['name']} to get ready...\n"
                response += '<script>' \
                            'setTimeout(function() {' \
                            ' window.location.replace(' \
                            f' window.location.pathname + "?uid={uid}"); ' \
                            '}, 2000);</script>'
                self.sendResponse(response)
                return
            else:
                if random.getrandbits(1) == 1:
                    player['state'] = 'move'
                    player['opponent']['state'] = 'stand'
                else:
                    player['state'] = 'stand'
                    player['opponent']['state'] = 'move'

        if player['state'] in ('move', 'again'):
            hit = parse_coords(args.get('hit'))
            field = player['opponent']['field']
            if hit is not None:
                line = field[hit[1]]
                if line[hit[0]] == ' ':
                    line = line[:hit[0]] + 'X' + line[hit[0] + 1:]
                    field[hit[1]] = line
                    ships = check_field(field)
                    if ships is not None and sum(ships) == 0:
                        player['state'] = 'won'
                        player['opponent']['state'] = 'lost'
                        history = [player] + history[:25]
                    else:
                        player['state'] = 'again'
                else:
                    if line[hit[0]] == '.':
                        line = line[:hit[0]] + 'O' + line[hit[0] + 1:]
                        field[hit[1]] = line
                    player['state'] = 'stand'
                    player['opponent']['state'] = 'move'

        if player['state'] == 'stand':
            response = f"<p>{player['name']}, you're playing with {player['opponent']['name']}"
            response += '<p> ' \
                        '<pre>'
            mine = draw_field(player['field'], True)
            their = draw_field(player['opponent']['field'], False)
            for y in range(len(mine)):
                response += mine[y] + '    ' + their[y] + '\n'
            response += '</pre>'
            response += "<p>It's your opponent's move now. Stand by..."
            response += '<script>' \
                        'setTimeout(function() {' \
                        ' window.location.replace(' \
                        f' window.location.pathname + "?uid={uid}"); ' \
                        '}, 2000);</script>'
            self.sendResponse(response)
            return
        elif player['state'] in ('move', 'again'):
            response = f"<p>{player['name']}, you're playing with {player['opponent']['name']}"
            response += '<p> ' \
                        '<pre>'
            mine = draw_field(player['field'], True)
            their = draw_field(player['opponent']['field'], False)
            for y in range(len(mine)):
                response += mine[y] + '    ' + their[y] + '\n'
            response += '</pre>'
            if player['state'] == 'move':
                response += "<p>It's your move now."
            else:
                response += "<p>You've hit a ship, take an extra move"
            response += '<p><script>' \
                        'function keyPress(event) {' \
                        ' if (event.key == "Enter")' \
                        '  sendHit();' \
                        '}' \
                        'function sendHit() {' \
                        ' window.location.replace(window.location.pathname +' \
                        f' "?uid={uid}&hit=" + document.getElementById("hit").value);' \
                        '}</script>' \
                        '<label for="hit">Enter coordinates </label> ' \
                        '<input type="text" onkeypress="keyPress(event)" name="hit" id="hit" size=4 ' \
                        'oninput="this.value = this.value.toUpperCase()" autofocus/> ' \
                        '<label> to </label> ' \
                        '<button onclick="sendHit()">Fire</button>'
            self.sendResponse(response)
            return
        elif player['state'] in ('won', 'lost'):
            response = f"<p>{player['name']}, you've played with {player['opponent']['name']}"
            response += '<p> ' \
                        '<pre>'
            mine = draw_field(player['field'], True)
            their = draw_field(player['opponent']['field'], True)
            for y in range(len(mine)):
                response += mine[y] + '    ' + their[y] + '\n'
            response += '</pre>'
            if player['state'] == 'won':
                response += '<p><b>Congratulations! You have WON!</b>'
            else:
                response += '<p><b>The match is over. Your opponent has won.</b>'
            response += '<p><button onClick="(function()' \
                        '{ window.location.replace(window.location.pathname); }' \
                        ')(); return false;" autofocus>Start over</button>'
            self.sendResponse(response)
            return


def main():
    httpd = HTTPServer(('', 8080), RequestHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
