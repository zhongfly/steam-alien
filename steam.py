# encoding:UTF-8
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
    boss_zones = sorted((z for z in zones if not z['captured'] and z['type'] == 4),key=lambda x: x['zone_position'])
    if boss_zones:
        print('boss!\n',boss_zones)
        return boss_zones
    else:
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
            if zones[0]['difficulty'] == 1:
                planet = planets[-1]
                zones = getzone(planet['id'], difficulty_limit)
            else:
                pass
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
        print('分数发送失败\nError:', e)
        return False


def bug(access_token, score):
    print("\n====bug? try!=====")
    stillbug=True
    while stillbug == True:
        stillbug=upload(access_token, score)
    print('====bug====\n')


def play(access_token, zone_position, difficulty):
    try:
        r = requests.post(BASE_URL.format('JoinZone'), data={
                          'zone_position': str(zone_position), 'access_token': access_token, })
    except Exception as e:
        print('加入游戏失败\nError:', e)
        return False
    try:
        if r.json()['response'].__contains__('zone_info'):
            print('已成功加入，等待110s发送分数')
        time.sleep(110)
        erro = 0
        while erro < 4:
            if upload(access_token, score_dict[difficulty-1]):
                return True
            else:
                print('wait 5s')
                time.sleep(5)
                erro = erro+1
        else:
            print('分数发送失败已达4次，休息20s')
            time.sleep(20)
            return False
    except Exception as e:
        print('Error:', e)
        bug(access_token, score_dict[difficulty-1])
        reset(access_token,True,False,False)
        return False

def reset(access_token, resetzone=True, resetplanet=True, output=True, planet_id=False):
    playerinfo = get_playerinfo(access_token)
    if output:
        print('level:{} score:{}/{}'.format(playerinfo['level'],
                                            playerinfo['score'], playerinfo['next_level_score']))
    else:
        pass
    if playerinfo.__contains__('active_zone_game') and resetzone:
        leave(access_token, playerinfo['active_zone_game'])
        print('离开房间:{}'.format(playerinfo['active_zone_game']))
    else:
        pass
    if playerinfo.__contains__('active_planet') and resetplanet:
        leave(access_token, playerinfo['active_planet'])
        print('离开星球:{}'.format(playerinfo['active_planet']))
    else:
        pass
    if planet_id and planet_id != playerinfo['active_planet']:
        leave(access_token, playerinfo['active_planet'])
        print('离开星球:{}'.format(playerinfo['active_planet']))
    else:
        pass



def main(access_token):
    reset(access_token)
    planet_id = False
    while(1):
        print('\n'+time.asctime(time.localtime(time.time())))
        playerinfo = get_playerinfo(access_token)
        print('level:{} score:{}/{}'.format(playerinfo['level'],
                                            playerinfo['score'], playerinfo['next_level_score']))
        best = getbest(access_token)
        if playerinfo.__contains__('active_zone_game'):
            bug(access_token, score_dict[difficulty-1])
            leave(access_token, playerinfo['active_zone_game'])
        if playerinfo.__contains__('active_planet'):
            planet_id = playerinfo['active_planet']
        if best['id'] != planet_id:
            if planet_id:
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
