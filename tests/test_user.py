import requests

# 服务器地址
BASE_URL = "http://127.0.0.1:8000"

# 用户登录信息
username = "johndoe"
password = "password"


def get_access_token(username, password):
    url = f"{BASE_URL}/token"
    payload = {
        'username': username,
        'password': password
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(url, data=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception(f"Failed to get access token: {response.text}")


def get_user_info(access_token):
    url = f"{BASE_URL}/users/me/"
    headers = {
        'Authorization': f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get user info: {response.text}")


def main():
    try:
        access_token = get_access_token(username, password)
        print("Access Token:", access_token)

        user_info = get_user_info(access_token)
        print("User Info:", user_info)
    except Exception as e:
        print(str(e))


if __name__ == "__main__":
    main()
