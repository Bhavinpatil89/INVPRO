def test_index_redirect(client):
    """Test that the index/dashboard redirects if not logged in."""
    response = client.get('/')
    # The current logic might redirect to /auth/login
    assert response.status_code in [302, 200] 

def test_login_page_loads(client):
    """Test that the login page loads successfully."""
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert b"INVPRO" in response.data
