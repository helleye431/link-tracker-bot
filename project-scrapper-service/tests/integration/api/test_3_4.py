def test_3_4(client):
    link = "https://github.com/helleye431/asteroids"
    undefined_header = {"tg-chat-id": "999"}
    response1 = client.post("/tg-chat/1")
    response2 = client.request(
        "DELETE", "/links", json={"link": link}, headers=undefined_header
    )

    assert response1.status_code == 200
    assert response2.status_code == 404
