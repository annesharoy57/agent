<?php

namespace App\Http\Controllers;

use App\Models\User;
use App\Models\TripChatMessage;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class AccountController extends Controller
{
    public function registerForm()
    {
        return view('auth.register');
    }

    public function register(Request $request)
    {
        $data = $request->validate([
            'name' => ['required', 'string', 'max:100'],
            'email' => ['required', 'email', 'max:255', 'unique:users,email'],
            'password' => ['required', 'string', 'min:8', 'confirmed'],
        ]);

        $user = User::create($data);
        Auth::login($user);
        $this->importGuestHistory($request, $user);
        $request->session()->regenerate();
        $request->session()->forget('guest_chat_turns');

        return redirect()->route('home');
    }

    public function loginForm()
    {
        return view('auth.login');
    }

    public function login(Request $request)
    {
        $credentials = $request->validate([
            'email' => ['required', 'email'],
            'password' => ['required', 'string'],
        ]);

        if (!Auth::attempt($credentials, $request->boolean('remember'))) {
            return back()->withErrors(['email' => 'Those sign-in details do not match an account.'])->onlyInput('email');
        }

        $request->session()->regenerate();
        $this->importGuestHistory($request, Auth::user());
        $request->session()->forget('guest_chat_turns');
        return redirect()->route('home');
    }

    public function logout(Request $request)
    {
        Auth::logout();
        $request->session()->invalidate();
        $request->session()->regenerateToken();
        return redirect()->route('home');
    }

    private function importGuestHistory(Request $request, User $user): void
    {
        foreach ($request->session()->get('guest_chat_messages', []) as $message) {
            TripChatMessage::create([
                'user_id' => $user->id,
                'role' => $message['role'],
                'content' => $message['content'],
                'context' => $message['context'] ?? null,
            ]);
        }
        $request->session()->forget('guest_chat_messages');
    }
}
