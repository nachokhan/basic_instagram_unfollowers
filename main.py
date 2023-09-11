import json
import os
import codecs
import datetime
from instagram_private_api import (
        Client, ClientError, ClientLoginError,
        ClientCookieExpiredError, ClientLoginRequiredError,
        __version__ as client_version)

from user_and_pass import users_pass

settings_file_sufix = "settings"


def to_json(python_object):
    if isinstance(python_object, bytes):
        return {'__class__': 'bytes',
                '__value__': codecs.encode(python_object, 'base64').decode()}
    raise TypeError(repr(python_object) + ' is not JSON serializable')


def from_json(json_object):
    if '__class__' in json_object and json_object['__class__'] == 'bytes':
        return codecs.decode(json_object['__value__'].encode(), 'base64')
    return json_object


def onlogin_callback(session, new_settings_file):
    cache_settings = session.settings
    with open(new_settings_file, 'w') as outfile:
        json.dump(cache_settings, outfile, default=to_json)
        print('SAVED: {0!s}'.format(new_settings_file))


def login(username, password):
    try:
        settings_file = f"data/{username}_{settings_file_sufix}.json"
        if not os.path.isfile(settings_file):
            print(f'Unable to find file: {settings_file}')
            session = Client(username, password,on_login=lambda x: onlogin_callback(x, settings_file))
        else:
            with open(settings_file) as file_data:
                cached_settings = json.load(file_data, object_hook=from_json)
            print('Reusing settings: {0!s}'.format(settings_file))

            device_id = cached_settings.get('device_id')
            # reuse auth settings
            session = Client(username, password, settings=cached_settings)
    except (ClientCookieExpiredError, ClientLoginRequiredError) as e:
        print('ClientCookieExpiredError/ClientLoginRequiredError: {0!s}'.format(e))
    except ClientLoginError as e:
        print('ClientLoginError {0!s}'.format(e))
        exit(9)
    except ClientError as e:
        print('ClientError {0!s} (Code: {1:d}, Response: {2!s})'.format(e.msg, e.code, e.error_response))
        exit(9)
    except Exception as e:
        print('Unexpected Exception: {0!s}'.format(e))
        exit(99)
    # Show when login expires
    cookie_expiry = session.cookie_jar.auth_expires
    print('Cookie Expiry: {0!s}'.format(datetime.datetime.fromtimestamp(cookie_expiry).strftime('%Y-%m-%dT%H:%M:%SZ')))

    return session, settings_file


def do(username, password):

    # Creamos una sesión de Instagram
    # O utilizamos una existente
    session, cookie_file  = login(username, password)

    # Creamos las listas que utilizaremos para ver quien 
    # no nos quiere ver más. 
    followers_anteriores = []
    followers_actuales = []
    me_dejaron_de_seguir = []

    # PRIMERO: Obtenemos todos nuestros followers actuales.
    user_id = session.authenticated_user_id
    rank_token = session.generate_uuid()
    next_max_id = ""

    while True:
        try:
            results = session.user_followers(user_id, rank_token, max_id=next_max_id)
            followers_actuales.extend(results['users'])
            next_max_id = results.get('next_max_id')
            if not next_max_id:
                break
        except Exception as ClientError:
            print("Error in settings. File. Removing and trying again.")
            os.remove(cookie_file)
            session, cookie_file  = login(username, password)


    # SEGUNDO: Abrimos el archivo con nuestros followers anteriores.
    followers_file = f"data/{username}_followers.json"
    try:
        with open(followers_file) as f:
            followers_anteriores = json.load(f)
    except Exception:
        followers_anteriores = []


    # TERCERO: Vemos la diferencia de followers.
    set_anteriores = {f['pk'] for f in followers_anteriores}
    set_actuales = {f['pk'] for f in followers_actuales}
    no_me_quieren_pks = set_anteriores - set_actuales
    me_dejaron_de_seguir = [f for f in followers_anteriores if f['pk'] in no_me_quieren_pks]
    nuevos_seguidores = [f for f in followers_actuales if f['pk'] not in set_anteriores]


    # CUARTO: Guardamos los seguifores actuales para la proxima vez.
    with open(followers_file, "w") as f:
        f.write(json.dumps(followers_actuales))

    # CUARTO(2): Guardamos los que me dejaron de seguir en la lista negra.
    unfollowers_file = f"data/{username}_unfollowers.json"
    with open(unfollowers_file, "a") as f:
        f.write(json.dumps(me_dejaron_de_seguir) + "\n")


    # QUINTO: Mostramos los ex-seguidores
    if me_dejaron_de_seguir:
        print("YA NO ME QUIREN 😢: ")
        for persona_buena in me_dejaron_de_seguir:
            print(f"🙅🏻 {persona_buena['username']}")
    else:
        print("NADIE TE DEJO DE QUERER 😎")


    # SEXTO: Mostramos los nuevos seguidores.
    if nuevos_seguidores:
        print("MIS NUEVOS SEGUIDORES 😎:")
        for persona_buena in nuevos_seguidores:
            print(f"🙅🏻 {persona_buena['username']}")
    else:
        print("NO TENES SEGUIDORES NUEVOS 🫠")



if __name__ == "__main__":
    print("\n\n")
    for username in users_pass.keys():
        print("--------------------------------------------------------------------------")
        print(f"User: {username}")
        do(username, users_pass[username])
        print("--------------------------------------------------------------------------\n\n")