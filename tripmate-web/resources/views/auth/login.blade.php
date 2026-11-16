<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>Sign in to TripMate</title>
    <style>
        body{margin:0;background:#f3f5f1;color:#173b2d;font:16px Arial,sans-serif}.panel{max-width:440px;margin:8vh auto;padding:32px;background:#fff;border-radius:18px;box-shadow:0 14px 40px #173b2d18}h1{margin-top:0}label{display:block;margin:16px 0 6px}input{box-sizing:border-box;width:100%;padding:12px;border:1px solid #bdc9c0;border-radius:8px;font:inherit}button{margin-top:22px;width:100%;padding:13px;border:0;border-radius:8px;background:#173b2d;color:#fff;font:inherit;cursor:pointer}.error{color:#a32525}.muted{color:#59675e;line-height:1.5}a{color:#176144}
    </style>
</head>
<body>
<main class="panel">
    <h1>Welcome back</h1>
    @if ($errors->any()) <div class="error">{{ $errors->first() }}</div> @endif
    <form method="post" action="{{ route('login.store') }}">
        @csrf
        <label for="email">Email</label><input id="email" type="email" name="email" value="{{ old('email') }}" required autocomplete="email">
        <label for="password">Password</label><input id="password" type="password" name="password" required autocomplete="current-password">
        <label><input type="checkbox" name="remember" value="1" style="width:auto"> Remember me</label>
        <button type="submit">Sign in</button>
    </form>
    <p class="muted">New to TripMate? <a href="{{ route('register') }}">Create a free account</a></p>
</main>
</body>
</html>
