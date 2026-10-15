def signup(api, name="Mohit", password="secret1"):
    return api.post("/api/auth/signup", {"name": name, "password": password})


def test_signup_then_me(api):
    response = signup(api)
    assert response.status_code == 201
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['token']}")
    assert api.get("/api/auth/me").json()["name"] == "Mohit"


def test_signup_claims_a_name_added_by_a_friend(api, goa):  # Mohit was added without a password
    assert signup(api).status_code == 201
    assert signup(api, password="other1").status_code == 400  # now it's taken


def test_login(api):
    signup(api)
    assert api.post("/api/auth/login", {"name": "mohit", "password": "wrong1"}).status_code == 400
    assert api.post("/api/auth/login", {"name": "mohit", "password": "secret1"}).status_code == 200


def test_me_needs_a_valid_token(api):
    assert api.get("/api/auth/me").status_code == 401
    api.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
    assert api.get("/api/auth/me").status_code == 401


def test_core_api_stays_open_without_login(api):
    assert api.post("/api/users", {"name": "Zoya"}).status_code == 201
