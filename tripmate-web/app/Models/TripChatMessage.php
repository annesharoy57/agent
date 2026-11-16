<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class TripChatMessage extends Model
{
    protected $fillable = ['user_id', 'role', 'content', 'context'];

    protected function casts(): array
    {
        return ['context' => 'array'];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }
}
