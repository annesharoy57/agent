<?php

namespace App\Http\Controllers;

use App\Models\TripChatMessage;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Auth;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Validation\ValidationException;

class TripPlannerController extends Controller
{
    public function plan(Request $request)
    {
        $trip = $this->validatedTrip($request);
        $request->session()->forget('guest_chat_messages');
        $response = $this->forwardToAgent($trip, '/plan');
        if (Auth::check() && $response->getStatusCode() < 300) {
            $answer = $response->getData(true);
            TripChatMessage::create([
                'user_id' => Auth::id(), 'role' => 'user',
                'content' => 'Create a trip plan for ' . ($trip['destination'] ?? $trip['departure_city']),
                'context' => $trip,
            ]);
            TripChatMessage::create([
                'user_id' => Auth::id(), 'role' => 'assistant',
                'content' => $answer['itinerary'] ?? 'Trip plan created.',
                'context' => $trip,
            ]);
        }
        return $response;
    }

    public function recommend(Request $request)
    {
        $trip = $this->validatedTrip($request);
        $request->session()->forget('guest_chat_messages');
        return $this->forwardToAgent($trip, '/recommendations');
    }

    public function chat(Request $request)
    {
        $validated = $request->validate([
            'message' => ['required', 'string', 'max:500'],
            'history' => ['nullable', 'array', 'max:20'],
            'history.*.role' => ['required', 'in:user,assistant'],
            'history.*.content' => ['required', 'string', 'max:2000'],
            'plan_estimate' => ['nullable', 'array'],
            'plan_estimate.destination' => ['required_with:plan_estimate', 'string', 'max:150'],
            'plan_estimate.budget' => ['required_with:plan_estimate', 'numeric', 'gt:0'],
            'plan_estimate.currency' => ['required_with:plan_estimate', 'string', 'regex:/^[A-Za-z]{3}$/'],
            'plan_estimate.estimated_total' => ['required_with:plan_estimate', 'numeric', 'gte:0'],
            'plan_estimate.budget_difference' => ['required_with:plan_estimate', 'numeric'],
            'plan_estimate.within_budget' => ['required_with:plan_estimate', 'boolean'],
            'plan_estimate.breakdown' => ['required_with:plan_estimate', 'array'],
            'plan_estimate.breakdown.transport' => ['required_with:plan_estimate', 'numeric', 'gte:0'],
            'plan_estimate.breakdown.accommodation' => ['required_with:plan_estimate', 'numeric', 'gte:0'],
            'plan_estimate.breakdown.food' => ['required_with:plan_estimate', 'numeric', 'gte:0'],
            'plan_estimate.breakdown.activities' => ['required_with:plan_estimate', 'numeric', 'gte:0'],
            'plan_estimate.breakdown.local_travel' => ['required_with:plan_estimate', 'numeric', 'gte:0'],
            'plan_estimate.breakdown.contingency' => ['required_with:plan_estimate', 'numeric', 'gte:0'],
            'trip' => ['required', 'array'],
            'trip.budget' => ['required', 'numeric', 'gt:0'],
            'trip.currency' => ['required', 'string', 'regex:/^[A-Za-z]{3}$/'],
            'trip.duration_days' => ['required', 'integer', 'between:1,30'],
            'trip.departure_city' => ['required', 'string', 'max:100'],
            'trip.start_date' => ['required', 'date'],
            'trip.travel_scope' => ['nullable', 'in:local,domestic,Bangladesh,international,anywhere'],
            'trip.interests' => ['nullable', 'array'],
            'trip.interests.*' => ['string', 'max:50'],
            'trip.destination' => ['nullable', 'string', 'max:150'],
            'trip.travelers' => ['nullable', 'integer', 'between:1,100'],
            'trip.trip_type' => ['nullable', 'in:single,group'],
            'trip.contribution_per_person' => ['required_if:trip.trip_type,group', 'nullable', 'numeric', 'gt:0'],
            'trip.travel_style' => ['nullable', 'in:budget,balanced,premium'],
            'trip.additional_preferences' => ['nullable', 'string', 'max:1000'],
            'trip.feedback' => ['nullable', 'string', 'max:300'],
            'trip.excluded_destinations' => ['nullable', 'array', 'max:20'],
            'trip.excluded_destinations.*' => ['string', 'max:100'],
            'trip.first_visit' => ['nullable', 'boolean'],
            'trip.visited_places' => ['nullable', 'array', 'max:40'],
            'trip.visited_places.*' => ['string', 'max:120'],
        ]);

        if (!Auth::check() && $request->session()->get('guest_chat_turns', 0) >= 5) {
            $request->session()->put('pending_trip_context', $validated['trip']);
            return response()->json([
                'needs_signup' => true,
                'message' => 'You have used your five free assistant messages. Create a free account to keep chatting.',
                'signup_url' => route('register'),
            ], 429);
        }

        $trip = $this->normalizeTrip($validated['trip']);
        $trip['currency'] = strtoupper($trip['currency']);
        $trip['travel_scope'] = $trip['travel_scope'] ?? 'anywhere';
        $trip['interests'] = $trip['interests'] ?? [];
        $trip['travelers'] = $trip['travelers'] ?? 1;
        $trip['travel_style'] = $trip['travel_style'] ?? 'balanced';
        $trip['additional_preferences'] = $trip['additional_preferences'] ?? '';
        $trip['feedback'] = $trip['feedback'] ?? '';
        $trip['excluded_destinations'] = $trip['excluded_destinations'] ?? [];
        $trip['visited_places'] = $trip['visited_places'] ?? [];
        $payload = [
            'message' => $validated['message'],
            'trip' => $trip,
            'history' => $validated['history'] ?? [],
            'plan_estimate' => $validated['plan_estimate'] ?? null,
        ];
        $response = $this->forwardToAgent($payload, '/chat');
        if (Auth::check() && $response->getStatusCode() < 300) {
            $answer = $response->getData(true);
            TripChatMessage::create([
                'user_id' => Auth::id(),
                'role' => 'user',
                'content' => $validated['message'],
                'context' => $trip,
            ]);
            TripChatMessage::create([
                'user_id' => Auth::id(),
                'role' => 'assistant',
                'content' => $answer['reply'] ?? 'TripMate updated the recommendations.',
                'context' => [
                    'trip' => $trip,
                    'answer_media' => $answer['answer_media'] ?? [],
                    'answer_sources' => $answer['answer_sources'] ?? [],
                ],
            ]);
        } elseif ($response->getStatusCode() < 300) {
            $request->session()->increment('guest_chat_turns');
            $answer = $response->getData(true);
            $guestMessages = $request->session()->get('guest_chat_messages', []);
            $guestMessages[] = ['role' => 'user', 'content' => $validated['message'], 'context' => $trip];
            $guestMessages[] = ['role' => 'assistant', 'content' => $answer['reply'] ?? '', 'context' => [
                'trip' => $trip,
                'answer_media' => $answer['answer_media'] ?? [],
                'answer_sources' => $answer['answer_sources'] ?? [],
            ]];
            $request->session()->put('guest_chat_messages', array_slice($guestMessages, -10));
        }
        return $response;
    }

    public function chatHistory(Request $request)
    {
        if (!Auth::check()) {
            return response()->json([
                'messages' => $request->session()->get('guest_chat_messages', []),
            ]);
        }

        $messages = TripChatMessage::query()
            ->where('user_id', Auth::id())
            ->latest('id')
            ->limit(50)
            ->get(['role', 'content', 'created_at', 'context'])
            ->reverse()
            ->values();

        return response()->json(['messages' => $messages]);
    }

    private function validatedTrip(Request $request): array
    {
        $validated = $request->validate([
            'budget' => ['required', 'numeric', 'gt:0'],
            'currency' => ['required', 'string', 'regex:/^[A-Za-z]{3}$/'],
            'duration_days' => ['required', 'integer', 'between:1,30'],
            'departure_city' => ['required', 'string', 'max:100'],
            'start_date' => ['required', 'date', 'after_or_equal:today'],

            'travel_scope' => [
                'required',
                'in:local,domestic,Bangladesh,international,anywhere',
            ],

            'interests' => ['nullable', 'array'],
            'interests.*' => ['string', 'max:50'],

            'destination' => ['nullable', 'string', 'max:150'],
            'feedback' => ['nullable', 'string', 'max:300'],
            'excluded_destinations' => ['nullable', 'array', 'max:20'],
            'excluded_destinations.*' => ['string', 'max:100'],
            'first_visit' => ['nullable', 'boolean'],
            'visited_places' => ['nullable', 'array', 'max:40'],
            'visited_places.*' => ['string', 'max:120'],
            'travelers' => ['nullable', 'integer', 'between:1,100'],
            'trip_type' => ['nullable', 'in:single,group'],
            'contribution_per_person' => ['required_if:trip_type,group', 'nullable', 'numeric', 'gt:0'],

            'travel_style' => [
                'nullable',
                'string',
                'in:budget,balanced,premium',
            ],

            'additional_preferences' => [
                'nullable',
                'string',
                'max:1000',
            ],
        ]);

        return $this->normalizeTrip($validated);
    }

    private function normalizeTrip(array $trip): array
    {
        $trip['travelers'] = (int) ($trip['travelers'] ?? 1);
        if (!array_key_exists('trip_type', $trip) && $trip['travelers'] > 1) {
            $trip['trip_type'] = 'group';
            $trip['contribution_per_person'] = (float) $trip['budget'] / $trip['travelers'];
        } else {
            $trip['trip_type'] = $trip['trip_type'] ?? 'single';
        }
        if ($trip['trip_type'] === 'group') {
            if ($trip['travelers'] < 2) {
                throw ValidationException::withMessages([
                    'travelers' => 'A group tour must include at least two members.',
                ]);
            }
            if (!isset($trip['contribution_per_person'])) {
                throw ValidationException::withMessages([
                    'contribution_per_person' => 'Enter each group member’s contribution.',
                ]);
            }
            $trip['budget'] = (float) $trip['contribution_per_person'] * $trip['travelers'];
        } else {
            $trip['travelers'] = 1;
            $trip['contribution_per_person'] = (float) $trip['budget'];
        }

        $trip['currency'] = strtoupper($trip['currency']);
        $trip['interests'] = $trip['interests'] ?? [];
        $trip['travel_style'] = $trip['travel_style'] ?? 'balanced';
        $trip['additional_preferences'] = $trip['additional_preferences'] ?? '';
        $trip['feedback'] = $trip['feedback'] ?? '';
        $trip['excluded_destinations'] = $trip['excluded_destinations'] ?? [];
        $trip['visited_places'] = $trip['visited_places'] ?? [];
        $trip['first_visit'] = $trip['first_visit'] ?? null;

        return $trip;
    }

    private function forwardToAgent(array $validated, string $path)
    {
        try {
            $agentUrl = rtrim(
                config('services.tripmate.url', 'http://127.0.0.1:8001'),
                '/'
            );

            $response = Http::timeout(90)->post(
                $agentUrl . $path,
                $validated
            );

            if ($response->failed()) {
                logger()->error(
                    'TripMate Python agent returned an error.',
                    [
                        'status' => $response->status(),
                        'response' => $response->json(),
                    ]
                );

                return response()->json([
                    'message' => 'TripMate could not generate your travel plan. Please try again.',
                    'error' => $response->json(),
                ], 502);
            }

            return response()->json($response->json(), 200);

        } catch (ConnectionException $e) {
            logger()->error(
                'TripMate Python agent connection failed.',
                [
                    'error' => $e->getMessage(),
                ]
            );

            return response()->json([
                'message' => 'Cannot connect to the Python agent. Make sure FastAPI is running on port 8001.',
            ], 503);
        }
    }
}
