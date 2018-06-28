# encoding:UTF-8
# python3.6
import requests
import json
import time


difficulty_dict = ['低', '中', '高']
score_dict = ['600', '1200', '2400']


def get_planets():
    r = requests.get('https://community.steam-api.com/ITerritoryControlMinigameService/GetPlanets/v0001/',
                     params={"active_only": "1", "language": "schinese"})
    planets = r.json()['response']['planets']
    return planets


def select_planets(planets):
    idlist = []
    for planet in planets:
        planet_id = planet['id']
        idlist.append(planet_id)
        name = planet['state']['name']
        progress = planet['state']['capture_progress']
        print('星球id：{}  星球名：{}  进度：{}'.format(planet_id, name, progress))
    flag = 0
    while(flag == 0):
        select_id = input('请输入要进行游戏的星球的数字id：')
        try:
            if select_id in idlist:
                print('已成功选择')
                flag = 1
            else:
                print('输入错误，请确定输入的id可用')
        except Exception as e:
            print('Error:', e)
    return select_id


def autoselect_planets(planets):
    progress = 1
    for planet in planets:
        if planet['state']['capture_progress'] < progress:
            progress = planet['state']['capture_progress']
            select_id = planet['id']
            name = planet['state']['name']
        else:
            pass
    print('星球id：{}  星球名：{}  进度：{}'.format(select_id, name, progress))# encoding:UTF-8
# python3.6
import requests
import sys
import time


difficulty_dict = ['低', '中', '高']
score_dict = ['600', '1200', '2400']
blacklist = {'1': [], '2': [], '3': []}
difficulty = 3
BASE_URL = 'https://community.steam-api.com/ITerritoryControlMinigameService/{}/v0001?language=schinese'


def get_planets(difficulty_limit=1):
    r = requests.get(BASE_URL.format('GetPlanets'),
                     params={"active_only": "1"})
    planets = r.json()['response']['planets']
    def exp(p): 
        return p if p['id'] not in blacklist[str(difficulty_limit)] and not p['state']['captured'] else False
    planets = sorted(filter(exp, planets),
                     key=lambda p: p['state']['capture_progress'])
    return planets


def getzone(planet_id, difficulty_limit=1):
    try:
        r = requests.get(BASE_URL.format('GetPlanet'), params={
                         'id': '{}'.format(planet_id)})
    except Exception as e:
        print('Error:', e)
    data = r.json()['response']['planets'][0]
    name = data['state']['name']
    zones = data['zones']
    def exp(z):
        return z if z['difficulty'] >= difficulty_limit and not z['captured'] and z['capture_progress'] < 0.97 else False
    zones = sorted(filter(exp, zones),
                   key=lambda z: z['difficulty'], reverse=True)
    return zones


def choose(difficulty_limit):
    global blacklist
    select = {}
    planets = get_planets(difficulty_limit)
    for planet in planets:
        zones = getzone(planet['id'], difficulty_limit)
        if zones:
            zone = zones[0]
            select['zone_position'] = zone['zone_position']
            select['difficulty'] = zone['difficulty']
            select['zone_progress'] = zone['capture_progress']
            select['id'] = planet['id']
            select['name'] = planet['state']['name']
            select['planet_progress'] = planet['state']['capture_progress']
            break
        else:
            for n in range(difficulty_limit, 4):
                blacklist[str(n)].append(planet['id'])
            pass
    if select:
        return select
    else:
        return False


def getbest(access_token):
    global difficulty
    flag = 1
    while(flag):
        best = choose(difficulty)
        if best:
            flag = 0
            difficulty = best['difficulty']
            return best
        else:
            if difficulty > 1:
                difficulty = difficulty-1
                print('找不到有 {} 难度房间存在的星球，降低难度到 {} ，重新寻找'.format(
                    difficulty_dict[difficulty], difficulty_dict[difficulty-1]))
            else:
                print('找不到有 {} 难度房间存在的星球，60s后再寻找'.format(
                    difficulty_dict[difficulty-1]))
                time.sleep(60)
    else:
        pass


def joinplanet(access_token, planet_id):
    requests.post(BASE_URL.format('JoinPlanet'), params={
                  'id': planet_id, 'access_token': access_token})


def leave(access_token, gameid):
    requests.post('https://community.steam-api.com/IMiniGameService/LeaveGame/v0001/',
                  params={'gameid': gameid, 'access_token': access_token})


def get_playerinfo(access_token):
    r = requests.post(BASE_URL.format('GetPlayerInfo'),
                      data={'access_token': access_token})
    data = r.json()['response']
    return data


def upload(access_token, score):
    try:
        r = requests.post(BASE_URL.format('ReportScore'), data={
                          'access_token': access_token, 'score': score})
        result = r.json()['response']
        if result.__contains__('new_score'):
            print('分数发送成功，目前经验值：{}'.format(result['new_score']))
            return True
        else:
            return False
    except Exception as e:
        print('分数发送失败，5s后重试\nError:', e)
        time.sleep(5)
        return False


def play(access_token, zone_position, difficulty):
    try:
        r = requests.post(BASE_URL.format('JoinZone'), data={
                          'zone_position': str(zone_position), 'access_token': access_token, })
    except Exception as e:
        print('加入游戏失败\nError:', e)
        return False
    if r.json()['response'].__contains__('zone_info'):
        print('已成功加入，等待110s发送分数')
    else:
        get_playerinfo(access_token)
    time.sleep(110)
    erro = 0
    while erro < 4:
        if upload(access_token, score_dict[difficulty-1]):
            return True
        else:
            erro = erro+1
    else:
        print('分数发送失败已达4次，休息20s')
        time.sleep(20)
        return False


def reset(access_token, resetall=True, output=True):
    playerinfo = get_playerinfo(access_token)
    if output:
        print('level:{} score:{}/{}'.format(playerinfo['level'],
                                            playerinfo['score'], playerinfo['next_level_score']))
    if playerinfo.__contains__('active_zone_game'):
        leave(access_token, playerinfo['active_zone_game'])
        print('离开房间:{}'.format(playerinfo['active_zone_game']))
    if playerinfo.__contains__('active_planet') and resetall:
        leave(access_token, playerinfo['active_planet'])
        print('离开星球:{}'.format(playerinfo['active_planet']))


def main(access_token):
    reset(access_token)
    planet_id = None
    while(1):
        print('\n'+time.asctime(time.localtime(time.time())))
        reset(access_token, False)
        best = getbest(access_token)
        if best['id'] != planet_id:
            if planet_id != None:
                leave(access_token, planet_id)
            else:
                pass
            planet_id = best['id']
            joinplanet(access_token, planet_id)
        else:
            pass
        planet_info = '{}\n星球id：{}  星球名：{}  进度：{}'.format(time.asctime(
            time.localtime(time.time())), best['id'], best['name'], best['planet_progress'])
        print(planet_info)
        z_d = best['difficulty']
        zone_info = '已选择房间 {}(进度：{})，难度为：{}，预计获得的分数:{}'.format(
            best['zone_position'], best['zone_progress'], difficulty_dict[z_d-1], score_dict[z_d-1])
        print(zone_info)
        play(access_token, best['zone_position'], z_d)


if __name__ == '__main__':
    if len(sys.argv)>1:
        access_token= str(sys.argv[1])
    else:
        access_token = input('请输入token：')
    while(1):
        try:
            main(access_token)
        except Exception as e:
            print('=============\nError:', e)

    return select_id


def joinplanet(access_token, planet_id):
    requests.post('https://community.steam-api.com/ITerritoryControlMinigameService/JoinPlanet/v0001/',
                  params={'id': planet_id, 'access_token': access_token})


def autoselect_zone(planet_id, difficulty_limit=1):
    r = requests.get('https://community.steam-api.com/ITerritoryControlMinigameService/GetPlanet/v0001/',
                     params={'id': '{}'.format(planet_id), "language": "schinese"})
    data = r.json()['response']['planets'][0]
    name = data['state']['name']
    zones = data['zones']
    position = {}
    position['2'] = []
    position['1'] = []
    for zone in zones:
        if zone['captured'] == False:
            difficulty = zone['difficulty']
            if difficulty == 3:
                select_zone = zone['zone_position']
                break
            elif difficulty >= difficulty_limit:
                position[str(difficulty)].append(zone['zone_position'])
    else:
        if position['2'] != []:
            select_zone = position['2'][0]
            difficulty = 2
        elif position['1'] != []:
            select_zone = position['1'][0]
            difficulty = 1
        else:
            select_zone = None
            difficulty = None
    return [name, select_zone, difficulty]


def select_zone(planet_id, select_zone):
    r = requests.get('https://community.steam-api.com/ITerritoryControlMinigameService/GetPlanet/v0001/',
                     params={'id': '{}'.format(planet_id), "language": "schinese"})
    data = r.json()['response']['planets'][0]
    name = data['state']['name']
    zones = data['zones']
    for zone in zones:
        if zone['zone_position'] == int(select_zone):
            if zone['captured'] == False:
                difficulty = zone['difficulty']
                return [name, select_zone, difficulty]
            else:
                print('该位置已经被占领，请重新选择')
                return [name, None]
            break
        else:
            pass
    else:
        print('未找到该位置，请重新选择')
        return [name, None]


def leave(access_token, gameid):
    requests.post('https://community.steam-api.com/IMiniGameService/LeaveGame/v0001/',
                  params={'gameid': gameid, 'access_token': access_token})


def get_playerinfo(access_token):
    r = requests.post('https://community.steam-api.com/ITerritoryControlMinigameService/GetPlayerInfo/v0001/',
                      data={'access_token': access_token})
    data = r.json()['response']
    return data


def upload(access_token, score):
    post_data = {'access_token': access_token,
                 'score': score, "language": "schinese"}
    r = requests.post(
        'https://community.steam-api.com/ITerritoryControlMinigameService/ReportScore/v0001/', data=post_data)
    result = r.json()['response']
    if result.__contains__('new_score'):
        print('分数发送成功，目前经验值：{}'.format(result['new_score']))
        return True
    else:
        print('分数发送失败')
        return False


def play(access_token, zone_position, difficulty):
    r = requests.post('https://community.steam-api.com/ITerritoryControlMinigameService/JoinZone/v0001/',
                      data={'zone_position': str(zone_position), 'access_token': access_token, })
    if r.json()['response'].__contains__('zone_info'):
        print('已成功加入，等待110s发送分数')
    else:
        get_playerinfo(access_token)
    time.sleep(110)
    if upload(access_token, score_dict[difficulty-1]) == False:
        erro = 0
        while erro < 4:
            time.sleep(5)
            if upload(access_token, score_dict[difficulty-1]):
                return True
            else:
                erro = erro+1
        else:
            return False
    else:
        return True


def reset(access_token, resetall=True, output=True):
    playerinfo = get_playerinfo(access_token)
    if output:
        print('level:{} score:{}/{}\n'.format(playerinfo['level'],
                                              playerinfo['score'], playerinfo['next_level_score']))
    if playerinfo.__contains__('active_zone_game'):
        leave(access_token, playerinfo['active_zone_game'])
        print('leavezone:{}'.format(playerinfo['active_zone_game']))
    if playerinfo.__contains__('active_planet') and resetall:
        leave(access_token, playerinfo['active_planet'])
        print('leaveplanet:{}'.format(playerinfo['active_planet']))


access_token = input('请输入token：')
planets = get_planets()
difficulty_limit = int(
    input('3 高难度；2 中等难度；1 低难度（即所有难度均加入）\n请输入加入房间的最低难度（输入纯数字）：'))
if input('是否自动更换星球(y/n):') != 'n':
    planets_function = autoselect_planets
    zone_function = autoselect_zone
else:
    planets_function = select_planets
    if input('是否自动更换房间(y/n):') != 'n':
        zone_function = autoselect_zone
    else:
        zone_function = select_zone
reset(access_token)
planet_id = planets_function(planets)
joinplanet(access_token, planet_id)
pause = 0
while(pause == 0):
    print('\n'+time.asctime(time.localtime(time.time())))
    reset(access_token, False)
    if planets_function == autoselect_planets:
        planets = get_planets()
        new_planet = planets_function(planets)
        if new_planet != planet_id:
            leave(access_token, planet_id)
            joinplanet(access_token, planet_id)
        else:
            pass
    if zone_function == autoselect_zone:
        zone_data = autoselect_zone(planet_id, difficulty_limit)
    else:
        zone_data = select_zone(planet_id, input('房间位置(纯数字):'))

    if zone_data[1] != None:
        zone_position = zone_data[1]
        difficulty = zone_data[2]
        print('已选择房间 {}，难度为：{}，预计获得的分数:{}'.format(zone_position, difficulty_dict[difficulty-1], score_dict[difficulty-1]))
        if play(access_token, zone_position, difficulty) == False:
            reset(access_token, False, False)
        else:
            pass
    else:
        print('{}没有可以进行游戏的房间了，重新选择星球'.format(zone_data[0]))
        if planets_function != autoselect_planets:
            planet_id = select_planets(planets)
