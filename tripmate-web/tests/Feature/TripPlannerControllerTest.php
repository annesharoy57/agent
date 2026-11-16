<?php

namespace Tests\Feature;

use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class TripPlannerControllerTest extends TestCase
{
    public function test_group_budget_is_forwarded_as_member_count_times_contribution(): void
    {
        Http::fake([
            '127.0.0.1:8001/recommendations' => Http::response(['recommendations' => []]),
        ]);

        $response = $this->postJson(route('trip.recommendations'), [
            'budget' => 10000,
            'currency' => 'BDT',
            'duration_days' => 2,
            'departure_city' => 'Dhaka',
            'start_date' => now()->toDateString(),
            'travel_scope' => 'local',
            'trip_type' => 'group',
            'travelers' => 4,
            'contribution_per_person' => 5000,
        ]);

        $response->assertOk();
        Http::assertSent(fn ($request) =>
            $request->url() === 'http://127.0.0.1:8001/recommendations'
            && (float) $request['budget'] === 20000.0
            && $request['travelers'] === 4
            && $request['trip_type'] === 'group'
            && $request['contribution_per_person'] === 5000
        );
    }

    public function test_group_tour_requires_at_least_two_members(): void
    {
        $response = $this->postJson(route('trip.recommendations'), [
            'budget' => 5000,
            'currency' => 'BDT',
            'duration_days' => 2,
            'departure_city' => 'Dhaka',
            'start_date' => now()->toDateString(),
            'travel_scope' => 'local',
            'trip_type' => 'group',
            'travelers' => 1,
            'contribution_per_person' => 5000,
        ]);

        $response->assertUnprocessable()
            ->assertJsonValidationErrors('travelers');
    }

    public function test_chat_accepts_a_past_start_date_for_an_existing_trip(): void
    {
        Http::fake([
            '127.0.0.1:8001/chat' => Http::response([
                'reply' => 'Check the current local forecast.',
                'answer_media' => [],
                'answer_sources' => [],
            ]),
        ]);

        $response = $this->postJson(route('trip.chat'), [
            'message' => 'What should I pack?',
            'trip' => [
                'budget' => 10000,
                'currency' => 'BDT',
                'duration_days' => 2,
                'departure_city' => 'Dhaka',
                'start_date' => now()->subDay()->toDateString(),
                'travel_scope' => 'local',
                'destination' => 'Cox\'s Bazar',
            ],
            'plan_estimate' => [
                'destination' => 'Cox\'s Bazar',
                'budget' => 10000,
                'currency' => 'BDT',
                'estimated_total' => 8000,
                'budget_difference' => 2000,
                'within_budget' => true,
                'breakdown' => [
                    'transport' => 2000,
                    'accommodation' => 2000,
                    'food' => 1500,
                    'activities' => 1000,
                    'local_travel' => 1000,
                    'contingency' => 500,
                ],
            ],
        ]);

        $response->assertOk()
            ->assertJsonPath('reply', 'Check the current local forecast.');
        Http::assertSent(fn ($request) =>
            $request->url() === 'http://127.0.0.1:8001/chat'
            && $request['plan_estimate']['estimated_total'] === 8000
            && $request['plan_estimate']['breakdown']['transport'] === 2000
        );
    }
}
