<content>
<?php

namespace App\Http\Controllers;

use App\Models\User;
use App\Http\Requests\UpdateProfileRequest;
use Illuminate\Http\Request;

class ProfileController extends Controller
{
    /**
     * Update the user's profile.
     *
     * @param  \App\Http\Requests\UpdateProfileRequest  $request
     * @return \Illuminate\Http\Response
     */
    public function update(UpdateProfileRequest $request)
    {
        $user = auth()->user();
        
        // Only update allowed fields
        $data = $request->only([
            'name', 'email', 'password', 'avatar', 'bio', 'phone', 'website'
        ]);
        
        // Hash password if provided
        if (isset($data['password'])) {
            $data['password'] = bcrypt($data['password']);
        }
        
        $user->update($data);
        
        return response()->json([
            'message' => 'Profile updated successfully',
            'user' => $user
        ]);
    }
}