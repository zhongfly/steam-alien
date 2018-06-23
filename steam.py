# encoding:UTF-8
# python3.6
import requests
import json
import time


difficulty_dict = ['低', '中', '高']
score_dict = ['595', '1190', '2380']


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
    print('星球id：{}  星球名：{}  进度：{}'.format(select_id, name, progress))
    return select_id


def joinplanet(access_token, planet_id):
    requests.post('https://community.steam-api.com/ITerritoryControlMinigameService/JoinPlanet/v0001/',
                  params={'id': planet_id, 'access_token': access_token})


def leave(access_token, planet_id):
    requests.post('https://community.steam-api.com/ITerritoryControlMinigameService/LeaveGame/v0001/',
                  params={'id': planet_id, 'access_token': access_token})


def autoselect_zone(planet_id, difficulty_limit=1):
    r = requests.get('https://community.steam-api.com/ITerritoryControlMinigameService/GetPlanet/v0001/',
                     params={'id': '{}'.format(planet_id), "language": "schinese"})
    data = r.json()['response']['planets'][0]
    name = data['state']['name']
    zones = data['zones']
    zones.reverse()
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


def get_playerinfo(access_token):
    r = requests.post('https://community.steam-api.com/ITerritoryControlMinigameService/GetPlayerInfo/v0001/',
                      data={'access_token': access_token})
    data = r.json()['response']
    return data


def play(access_token, zone_position, difficulty):

    r = requests.post('https://community.steam-api.com/ITerritoryControlMinigameService/JoinZone/v0001/',
                      data={'zone_position': str(zone_position), 'access_token': access_token, })
    try:
        progress = r.json()['response']['zone_info']['capture_progress']
        print('已成功加入，等待2min发送分数')
        post_data = {'access_token': access_token,
                     'score': score_dict[difficulty-1], "language": "schinese"}
        time.sleep(120)
        r = requests.post(
            'https://community.steam-api.com/ITerritoryControlMinigameService/ReportScore/v0001/', data=post_data)
        result = r.json()['response']
        if result.__contains__('new_score'):
            print('分数发送成功，目前经验值：{}'.format(result['new_score']))
            return [True, result]
        else:
            print('分数发送失败')
            return [False, 1]
    except Exception as e:
        print('Error:', e)
        return [False, 0]


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


playerinfo = get_playerinfo(access_token)
print('level:{} score:{}/{}\n'.format(playerinfo['level'],
                                      playerinfo['score'], playerinfo['next_level_score']))
planet_id = planets_function(planets)
if  playerinfo.__contains__('active_planet') and playerinfo['active_planet'] != None:
    leave(access_token, playerinfo['active_planet'])

joinplanet(access_token, planet_id)
pause = 0
while(pause == 0):
    print('\n'+time.asctime(time.localtime(time.time())))
    playerinfo = get_playerinfo(access_token)
    print('level:{} score:{}/{}\n'.format(playerinfo['level'],
                                          playerinfo['score'], playerinfo['next_level_score']))
    if zone_function == autoselect_zone:
        zone_data = autoselect_zone(planet_id, difficulty_limit)
    else:
        zone_data = select_zone(planet_id, input('房间位置(纯数字):'))
    if zone_data[1] != None:
        zone_position = zone_data[1]
        difficulty = zone_data[2]
        print('星球：{}\n已选择房间 {}，难度为：{}，预计获得的分数:{}'.format(
            zone_data[0], zone_position, difficulty_dict[difficulty-1], score_dict[difficulty-1]))
        info = play(access_token, zone_position, difficulty)
        if info[0] == False and info[1] == 0:
            pause = 1
        else:
            pass
    else:
        if planets_function == autoselect_planets:
            print('{}没有可以进行游戏的房间了，重新选择星球'.format(zone_data[0]))
            leave(access_token, planet_id)
            planets = get_planets()
            planet_id = planets_function(planets)
            joinplanet(access_token, planet_id)
        else:
            pass
