# encoding:UTF-8
# python3.6

import asyncio
import random
import aiohttp


score_dict = ['595', '1190', '2380']

BASE_URL = 'https://community.steam-api.com/ITerritoryControlMinigameService/' \
        '{}/v0001?language=schinese'


async def get_planets(session):
    planets = []
    async with session.get(BASE_URL.format('GetPlanets'),
                           params={"active_only": "1"}) as resp:
        if resp.status == 200:
            try:
                resp_json = await resp.json()
                planets = resp_json['response']['planets']
            except KeyError:
                return planets
        else:
            await asyncio.sleep(.5)
        return planets


def autoselect_planets(planets):
    select_id = ''
    keys = sorted(planets.keys(), key=lambda k: float(planets[k]['state']['capture_progress']))
    while keys:
        planet = planets.get(keys[0])
        try:
            current_progress = float(planet['state']['capture_progress'])
            if current_progress < 0.99999999:
                select_id = keys[0]
                break
            else:
                keys.remove(0)
        except (KeyError, ValueError):
            # we don't get a planet
            continue

    return select_id


async def joinplanet(session, access_token, planet_id):
    success = False
    async with session.post(BASE_URL.format('JoinPlanet'), data={
        'id': planet_id,
        'access_token': access_token
    }) as resp:
        if resp.status == 200:
            success = True
    if success:
        print('Player["{}"]: 加入星球["{}"]\n'.format(
            access_token[:10], planets[str(planet_id)]['state']['name']))


async def leave(session, access_token, planet_id):
    await session.post('https://community.steam-api.com/IMiniGameService/LeaveGame/v0001/', data={
        'gameid': planet_id,
        'access_token': access_token
    })
    print(access_token[:10], 'leave planet', planet_id)


async def get_zones(session, planet_id):
    resp = await session.get(BASE_URL.format('GetPlanet'), params={
        'id': planet_id,
        "language": "schinese"
    })
    if not resp or resp.status != 200:
        return None

    try:
        data = await resp.json()
        zones = data['response']['planets'][0]['zones']
    except KeyError:
        return []

    zones = sorted(filter(lambda z: not z['captured'], zones), key=lambda z: z['difficulty'],
                   reverse=True)

    return zones


async def getplayerinfo(session, access_token):
    async with session.post(BASE_URL.format('GetPlayerInfo'),
                            data={'access_token': access_token}) as resp:
        try:
            resp_json = await resp.json()
            current_planet = resp_json['response']['active_planet']
            current_zone = resp_json['response'].get('active_zone_position', None)
            if current_zone is not None:
                print('Player["{}"] Current In Game["{}"]'.format(access_token[:10], current_zone))
                return current_planet, current_zone
        except KeyError:
            current_planet = None
            pass

    current_zone = None
    if current_planet:
        await leave(session, access_token, current_planet)
    current_planet = autoselect_planets(planets)
    await joinplanet(session, access_token, current_planet)
    # let's join SteamCN
    await join_group(session, access_token, '103582791429777370')
    return current_planet, current_zone


async def join_group(session, access_token, clanid):
    await session.post(BASE_URL.format('RepresentClan'), data={
        'access_token': access_token,
        'clanid': clanid,
    })


async def play(session, access_token, zone_position):
    count = 0
    while True:
        resp = await session.post(BASE_URL.format('JoinZone'), data={
            'zone_position': zone_position,
            'access_token': access_token
        })

        if resp.status != 200:
            raise RequestError()
        try:
            resp_json = await resp.json()
            zone_info = resp_json['response']['zone_info']
            if zone_info['captured']:
                break
        except KeyError:
            raise RequestError()

        success = await upload_score(session, access_token, zone_info)
        count += 1
        if not success or count > 5:
            return


async def upload_score(session, access_token, zone_info):
        print('Player["{}"]: 加入区域["pos: {}, level: {}"]，等待 2min 发送分数'.format(
            access_token[:10], zone_info['zone_position'], zone_info.get('difficulty', 1)))
        # wait 110 second, then tell fat-G
        await asyncio.sleep(110)

        async def post_score(score=None):
            resp = await session.post(BASE_URL.format('ReportScore'), data={
                'access_token': access_token,
                'score': score or score_dict[zone_info.get('difficulty', 1) - 1],
                'language': 'schinese'
            })

            resp_json = await resp.json()
            new_score = resp_json['response'].get('new_score', None)
            return new_score is not None, new_score

        sucess, new_score = await post_score()
        if sucess:
            print('Player["{}"] 分数发送成功, 目前经验值: {}'.format(access_token[:10], new_score))
        else:
            print('Player["{}"] 分数发送失败, 再尝试一次'.format(access_token[:10]))
            await asyncio.sleep(.5)
            sucess, new_score = await post_score(0)
            if sucess:
                print('Player["{}"} 分数发送成功, 目前经验值: {}'.format(access_token[:10], new_score))
            else:
                print('Player["{}"] 分数发送失败, 尝试离开游戏再次加入'.format(access_token[:10]))

        print()
        return sucess


class RequestError(Exception):
    pass


async def main(loop):
    """Request all active planets first, then put all player in game"""
    global planets
    print("获取星球信息")
    async with aiohttp.ClientSession(loop=loop) as session:
        count = 0
        planets_list = []
        while count < 10:
            count += 1
            planets_list = await get_planets(session)
        if not planets_list:
            raise SystemExit("Can't fetch planets list")
    planets = {v['id']: v for v in planets_list}
    show_planets()
    for token in tokens:
        asyncio.ensure_future(task(token), loop=loop)


async def task(token):
    """Task of play game"""
    async with aiohttp.ClientSession() as session:
        while True:
            current_planet, current_zone = await getplayerinfo(session, token)
            if current_zone is not None:
                success = await upload_score(session, token, {'zone_position': current_zone})
                if not success:
                    await asyncio.sleep(150)
                # await leave(session, token, current_planet)
                # continue

            zones = await get_zones(session, current_planet)
            while zones:
                zone = zones[0]
                captured = zone.get('captured', False)
                if captured:
                    zones.remove(0)
                    continue

                try:
                    await play(session, token, zone['zone_position'])
                except RequestError:
                    break
            # leave planet and let us have a chance to choice other planet
            await leave(session, token, current_planet)


def show_planets():
    for pid, planet in planets.items():
        state = planet['state']
        print("星球: {:s}[{}]\t\t当前进度: {:.15f}".format(
            state.get('name', 'Unknow Planet'),
            pid,
            state.get('capture_progress', 1.0)))
    print()


planets = {}
# input your tokens here, likes:
# tokens = ['token_1', 'token_2']
tokens = []

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(main(loop))
    loop.run_forever()
