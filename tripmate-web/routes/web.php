<?php

use App\Http\Controllers\TripPlannerController;
use App\Http\Controllers\AccountController;
use Illuminate\Support\Facades\Route;
use Illuminate\Http\Request;

Route::get('/', function (Request $request) {
    return view('home', ['resumeTrip' => $request->session()->pull('pending_trip_context')]);
})->name('home');
Route::get('/register', [AccountController::class, 'registerForm'])->name('register');
Route::post('/register', [AccountController::class, 'register'])->name('register.store');
Route::get('/login', [AccountController::class, 'loginForm'])->name('login');
Route::post('/login', [AccountController::class, 'login'])->name('login.store');
Route::post('/logout', [AccountController::class, 'logout'])->name('logout');
Route::post('/plan-trip', [TripPlannerController::class, 'plan'])
    ->name('trip.plan');
Route::post('/recommendations', [TripPlannerController::class, 'recommend'])
    ->name('trip.recommendations');
Route::post('/trip-chat', [TripPlannerController::class, 'chat'])
    ->name('trip.chat');
Route::get('/trip-chat/history', [TripPlannerController::class, 'chatHistory'])
    ->name('trip.chat.history');
