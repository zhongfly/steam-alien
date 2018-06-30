# encoding:UTF-8
# python3.6
import requests
import sys
import os
import time
from threading import Thread
from multiprocessing.dummy import Pool as ThreadPool
import random

difficulty_dict = ['低', '中', '高', 'Boss']
score_dict = ['600', '1200', '2400', '???']
best_update = None
bestupdater_flag = 1
BASE_URL = 'https://community.steam-api.com/ITerritoryControlMinigameService/{}/v0001?language=schinese'


def load():
    if os.path.exists('token.txt'):
        users = []
        with open('token.txt', 'r', encoding="utf-8") as f:
            lines = f.readlines()
            flen = len(lines)
            for i in range(flen):
                data = lines[i].strip('\n').split('+')
                if len(data) == 2:
                    user = [data[0], data[1]]
                elif len(data) == 1:
                    name = data[0][-4:]
                    user = [name, data[0]]
                users.append(user)
        return users
    else:
        with open('token.txt', 'w', encoding="utf-8") as f:
            f.write('your_name+your_token\nhe_name+he_token\nher_name+her_token')
        return False


def get_planets():
    r = requests.get(BASE_URL.format('GetPlanets'),
                     params={"active_only": "1"})
    planets = r.json()['response']['planets']

    def exp(p):
        return p if not p['state']['captured'] else False
    planets = sorted(filter(exp, planets),
                     key=lambda p: p['state']['capture_progress'])
    return planets


def getzone(planet_id):
    try:
        r = requests.get(BASE_URL.format('GetPlanet'), params={
                         'id': '{}'.format(planet_id)})
    except Exception as e:
        print('Error:', e)
    data = r.json()['response']['planets'][0]
    name = data['state']['name']
    zones = data['zones']

    def real(zone):
        if zone.__contains__('capture_progress'):
            return True
        else:
            False
    zones = list(filter(real, zones))
    boss_zones = []
    boss_zones = sorted((z for z in zones if not z['captured'] and z['type'] == 4 and z['boss_active']),key=lambda x: x['zone_position'])
    if boss_zones:
        print(f"Find boss in {name}!\n")
        for z in boss_zones:
            z['difficulty']=4
    else:
        pass
    def exp(z):
        return z if not z['captured'] and 0 < z['capture_progress'] < 0.97 and z['type'] != 4 and z["zone_position"] != 0 else False
    others = sorted(filter(exp, zones),
                    key=lambda z: z['difficulty'], reverse=True)
    return boss_zones+others


def getbest():
    select = {'difficulty': 0}
    planets = get_planets()
    for planet in planets:
        zones = getzone(planet['id'])
        planet['zones'] = zones
        if zones:
            if zones[0]['difficulty'] > select['difficulty']:
                zone = zones[0]
                select['zone_position'] = zone['zone_position']
                select['difficulty'] = zone['difficulty']
                select['zone_progress'] = zone['capture_progress']
                select['id'] = planet['id']
                select['name'] = planet['state']['name']
                select['planet_progress'] = planet['state']['capture_progress']
    if select['difficulty'] == 1:
        planet = planets[-1]
        zone = planet['zones'][0]
        select['zone_position'] = zone['zone_position']
        select['difficulty'] = zone['difficulty']
        select['zone_progress'] = zone['capture_progress']
        select['id'] = planet['id']
        select['name'] = planet['state']['name']
        select['planet_progress'] = planet['state']['capture_progress']
    if select:
        return select
    else:
        print('Getbest functinon erro')
        return False


def bestupdater():
    global best_update
    while(bestupdater_flag):
        try:
            result = getbest()
            if result:
                best_update = result
                time.sleep(int(random.uniform(90, 110)))
            else:
                print('寻找最佳星球失败')
                pass
        except Exception as e:
            print('寻找最佳星球失败|Error:', e)

class worker:
    def __init__(self,data):
        self.access_token = data[1]
        self.botname = data[0]
        self.playerinfo = {}
        self.planet_id = ''
        self.best = {}
    def timestamp(self):
        t = time.strftime("%H:%M:%S", time.localtime())
        return'{} |{} |'.format(t, self.botname)
    def bestupdate(self,data):
        self.best=data
    def joinplanet(self, planet_id):
        requests.post(BASE_URL.format('JoinPlanet'), params={
                      'id': planet_id, 'access_token': self.access_token})
    def leave(self,gameid):
        requests.post('https://community.steam-api.com/IMiniGameService/LeaveGame/v0001/',
                      params={'gameid': gameid, 'access_token': self.access_token})
    def get_playerinfo(self,output=False):
        r = requests.post(BASE_URL.format('GetPlayerInfo'),
                          data={'access_token': self.access_token})
        self.playerinfo = r.json()['response']
        if output:
            info = 'level:{} score:{}/{}'.format(
                self.playerinfo['level'], self.playerinfo['score'], self.playerinfo['next_level_score'])
            print(self.timestamp(), info)
    def uploadboss(self):
        useheal = 0
        count = random.uniform(-60, 0)
        data = {
            'access_token': self.access_token,
            'use_heal_ability': str(useheal),
            'damage_to_boss': '1',
            'damage_taken': '0'
        }
        while(1):
            try:
                if count >= 120:
                    useheal += 1
                    count = 0
                    data['use_heal_ability'] = useheal
                    print(self.timestamp(), 'Using heal ability')
                r = requests.post(BASE_URL.format('ReportBossDamage'), data=data)
                print(r.text)
                if r.json()['eresult'] == 1:
                    break
                result = r.json()['response']
                if result.__contains__('boss_status'):
                    boss_status = result['boss_status']
                    print("{}".format(result['boss_status']))
                if result['game_over']:
                    print(self.timestamp(), 'Boss Dead')
                    break
                if result['waiting_for_players']:
                    print(self.timestamp(), 'waiting_for_players')
                info = "Boss HP:{}/{} Lasers: {} Team Heals: {}".fomat(
                    boss_status['boss_hp'], boss_status['boss_hp'], result['num_laser_uses'], result['num_team_heals'])
                print(self.timestamp(), info)
                count += 5
                time.sleep(5)
            except Exception as e:
                print(self.timestamp(), '分数发送失败|Error:', e)
                return False

    def boss(self):
        zone_position=self.best['zone_position']
        try:
            r = requests.post(BASE_URL.format('JoinBossZone'), data={
                              'zone_position': str(zone_position), 'access_token': self.access_token, })
        except Exception as e:
            print(self.timestamp(), '加入游戏失败|Error:', e)
            return False
        try:
            print(r.text)
            if r.json()['response'].__contains__('zone_info'):
                print(self.timestamp(), '已成功加入')
            else:
                print(self.timestamp(), r.text)
                print(self.timestamp(), r.headers['X-error_message'])
            if uploadboss():
                return True
        except Exception as e:
            print(self.timestamp(), 'Error:', e)
            self.reset(True, False, False)
            return False

    def bug(self):
        print(self.timestamp(), "====bug? try!=====")
        score=score_dict[self.best['difficulty']-1]
        stillbug = True
        while stillbug == True:
            stillbug = upload(self.access_token, score, self.botname)
        print(self.timestamp(), '====bug?====')

    def upload(self, score):
        try:
            r = requests.post(BASE_URL.format('ReportScore'), data={
                              'access_token': self.access_token, 'score': score})
            result = r.json()['response']
            if result.__contains__('new_score'):
                print(self.timestamp(), '分数发送成功，目前经验值：{}'.format(
                    result['new_score']))
                return True
            else:
                print(self.timestamp(), '分数发送失败', r.headers['X-error_message'])
                return False
        except Exception as e:
            print(self.timestamp(), '分数发送失败|Error:', e)
            return False

    def play(self):
        zone_position=self.best['zone_position']
        score=score_dict[self.best['difficulty']-1]
        try:
            r = requests.post(BASE_URL.format('JoinZone'), data={
                              'zone_position': str(zone_position), 'access_token': self.access_token, })
        except Exception as e:
            print(self.timestamp(), '加入游戏失败|Error:', e)
            return False
        try:
            if r.json()['response'].__contains__('zone_info'):
                print(self.timestamp(), '已成功加入，等待110s发送分数')
                time.sleep(110)
                erro = 0
                while erro < 4:
                    if self.upload(score):
                        return True
                    else:
                        print(self.timestamp(), 'wait 5s')
                        time.sleep(5)
                        erro = erro+1
                else:
                    print(self.timestamp(), '分数发送失败已达4次，休息20s')
                    time.sleep(20)
                    return False
            else:
                print(r.text)
                print(self.timestamp(), '加入游戏失败|', r.headers['X-error_message'])
                return False
        except Exception as e:
            print(self.timestamp(), 'Error:', e)
            self.bug(score)
            selfreset(True, False, False)
            return False

    def reset(self, resetzone=True, resetplanet=True, output=True, planet_id=False):
        self.get_playerinfo(output)
        playerinfo = self.playerinfo
        if playerinfo.__contains__('active_zone_game') and resetzone:
            self.leave(playerinfo['active_zone_game'])
            print(self.timestamp(), '离开房间:{}'.format(
                playerinfo['active_zone_game']))
        elif playerinfo.__contains__('active_boss_game') and resetzone:
            self.leave(playerinfo['active_boss_game'])
            print(self.timestamp(), '离开Boss房间:{}'.format(
                playerinfo['active_boss_game']))
        if playerinfo.__contains__('active_planet') and resetplanet:
            self.leave(playerinfo['active_planet'])
            print(self.timestamp(), '离开星球:{}'.format(
                playerinfo['active_planet']))
        else:
            pass
        if planet_id and planet_id != playerinfo['active_planet']:
            self.leave(playerinfo['active_planet'])
            print(self.timestamp(), '离开星球:{}'.format(
                playerinfo['active_planet']))
        else:
            pass
    def loop(self):
        self.get_playerinfo(True)
        if self.playerinfo.__contains__('active_zone_game'):
            if self.best.__contains__('difficulty'):
                if self.best['difficulty']<4:
                    self.bug()
            self.leave(self.playerinfo['active_zone_game'])

        self.bestupdate(best_update)
        z_d=self.best['difficulty']
        if self.playerinfo.__contains__('active_planet'):
            self.planet_id = self.playerinfo['active_planet']
        if self.best['id'] != self.planet_id:
            if self.planet_id:
                self.leave(planet_id)
            else:
                pass
            self.planet_id = self.best['id']
            self.joinplanet(self.planet_id)
        else:
            pass
        planet_info = '星球id：{}  星球名：{}  进度：{}'.format(
            self.best['id'], self.best['name'], self.best['planet_progress'])
        print(self.timestamp(), planet_info)
        zone_info = '已选择房间 {}(进度：{})，难度为：{}，预计获得的分数:{}'.format(
            self.best['zone_position'], self.best['zone_progress'], difficulty_dict[z_d-1], score_dict[z_d-1])
        print(self.timestamp(), zone_info)
        if z_d < 4:
            self.play()
        else:
            self.boss()

def handler(user):
    planet_id=0
    bot=worker(user)
    bot.reset()
    while(1):
        try:
            bot.loop()
        except Exception as e:
            t = time.strftime("%H:%M:%S", time.localtime())
            print('{} | {}|Error:'.format(t,user[0]), e)



def main():
    users = load()
    if not users:
        print('please check token.txt')
        return False
    planet_id = False
    updater = Thread(target=bestupdater)
    updater.start()
    pool = ThreadPool(len(users)+1)
    print('starting')
    time.sleep(10)
    pool.map(handler,users)
    pool.close()
    pool.join()
    bestupdater_flag = 0
    updater.join()


if __name__ == '__main__':
    main()
