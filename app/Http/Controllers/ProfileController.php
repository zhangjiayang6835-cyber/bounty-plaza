<content>
<?php

namespace App\Http\Controllers;

use App\Http\Requests\UpdateUserProfileRequest;
use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;

class ProfileController extends Controller
{
    /**
     * Display the user's profile.
     *
     * @return \Illuminate\Http\Response
     */
    public function show()
    {
        return Auth::user();
    }

    /**
     * Update the user's profile.
     *
     * @param \App\Http\Requests\UpdateUserProfileRequest $request
     * @return \Illuminate\Http\Response
     */
    public function update(UpdateUserProfileRequest $request)
    {
        $user = Auth::user();
        
        // Only allow updating whitelisted fields
        $validated = $request->validated();
        
        // Handle password separately for security
        if (isset($validated['password'])) {
            $validated['password'] = Hash::make($validated['password']);
        }
        
        $user->update($validated);
        
        return response()->json([
            'message' => 'Profile updated successfully',
            'user' => $user
        ]);
    }
}