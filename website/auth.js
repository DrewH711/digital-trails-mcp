const existingToken = sessionStorage.getItem('access_token');
const expires_in = sessionStorage.getItem('expires_in');

if (!existingToken){

    function base64url(buf) {
    return btoa(String.fromCharCode(...new Uint8Array(buf)))
        .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    } 
    const verifier = base64url(crypto.getRandomValues(new Uint8Array(32)));
    const challenge = base64url(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)));
    sessionStorage.setItem('pkce_verifier', verifier);

    const state = crypto.randomUUID();
    sessionStorage.setItem('oauth_state', state);

    const authUrl = new URL('http://localhost:8000/authorize');
    authUrl.searchParams.set('response_type', 'code');
    authUrl.searchParams.set('client_id', '2115cb1e-6f2a-4b68-ae1c-cfed8488301a');
    authUrl.searchParams.set('redirect_uri', 'http://localhost:5000/callback.html');
    authUrl.searchParams.set('code_challenge', challenge);
    authUrl.searchParams.set('code_challenge_method', 'S256');
    authUrl.searchParams.set('state', state);
    authUrl.searchParams.set('resource', 'http://localhost:8000/mcp');

    window.location = authUrl;
}