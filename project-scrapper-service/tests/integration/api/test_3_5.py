def test_3_5(client):
    link = "https://github.com/helleye431/asteroids"
    header = {"tg-chat-id": "1"}

    response1 = client.post("/tg-chat/1")
    response2 = client.delete("/tg-chat/1")
    response3 = client.post(
        "/links",
        json={"link": link, "tags": ["test1", "test2"], "filters": ["test_filter"]},
        headers=header,
    )

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response3.status_code == 404
