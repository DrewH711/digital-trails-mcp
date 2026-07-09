const params = new URLSearchParams(window.location.search);
const code = params.get('code');
const returnedState = params.get('state');

if (returnedState !== sessionStorage.getItem('oauth_state')) {
  throw new Error('State mismatch — possible CSRF');
}

const res = await fetch('http://localhost:8000/token', {
  method: 'POST',
  headers: {'Content-Type': 'application/x-www-form-urlencoded'},
  body: new URLSearchParams({
    grant_type: 'authorization_code',
    code,
    redirect_uri: 'http://localhost:5000/callback.html',
    client_id: '2115cb1e-6f2a-4b68-ae1c-cfed8488301a',
    code_verifier: sessionStorage.getItem('pkce_verifier'),
    resource: 'http://localhost:8000/mcp'
  }),
});

if (!res.ok) {
  document.body.textContent = 'Login failed: ' + await res.text();
} else {

  const { access_token, expires_in } = await res.json();
  sessionStorage.setItem('access_token', access_token);
  sessionStorage.setItem('expires_in', expires_in);
  window.location = '/index.html';
}