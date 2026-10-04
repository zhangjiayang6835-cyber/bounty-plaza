<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ProfileUpdateTest extends TestCase
{
    use RefreshDatabase;

    /**
     * Test that a user can update their own profile with allowed fields.
     *
     * @return void
     */
    public function test_user_can_update_profile_with_allowed_fields()
    {
        $user = User::factory()->create();
        $this->actingAs($user);

        $response = $this->putJson('/api/profile', [
            'name' => 'New Name',
            'email' => 'new@example.com',
            'bio' => 'Updated bio',
            'preferences' => [
                'theme' => 'dark',
                'language' => 'es'
            ]
        ]);

        $response->assertStatus(200);
        $response->assertJsonFragment([
            'message' => 'Profile updated successfully',
            'name' => 'New Name',
            'email' => 'new@example.com',
            'bio' => 'Updated bio',
        ]);
        
        // Check that the preferences were updated
        $this->assertDatabaseHas('users', [
            'id' => $user->id,
            'preferences->theme' => 'dark',
            'preferences->language' => 'es'
        ]);
    }

    /**
     * Test that a user cannot update their role to escalate privileges.
     *
     * @return void
     */
    public function test_user_cannot_update_role_to_escalate_privileges()
    {
        $user = User::factory()->create(['role' => 'user']);
        $this->actingAs($user);

        $response = $this->putJson('/api/profile', [
            'role' => 'admin',
            'is_admin' => true
        ]);

        $response->assertStatus(422);
        $response->assertJsonValidationErrors(['role', 'is_admin']);
        
        // Check that the user's role and admin status were not updated
        $this->assertDatabaseHas('users', [
            'id' => $user->id,
            'role' => 'user',
            'is_admin' => false
        ]);
    }

    /**
     * Test that a user cannot update their email to an existing one.
     *
     * @return void
     */
    public function test_user_cannot_update_email_to_existing_one()
    {
        $user1 = User::factory()->create(['email' => 'user1@example.com']);
        $user2 = User::factory()->create(['email' => 'user2@example.com']);
        
        $this->actingAs($user1);

        $response = $this->putJson('/api/profile', [
            'email' => 'user2@example.com'
        ]);

        $response->assertStatus(422);
        $response->assertJsonValidationErrors(['email']);
        
        // Check that the email was not updated
        $this->assertDatabaseHas('users', [
            'id' => $user1->id,
            'email' => 'user1@example.com'
        ]);
    }

    /**
     * Test that a user can update their password.
     *
     * @return void
     */
    public function test_user_can_update_password()
    {
        $user = User::factory()->create();
        $this->actingAs($user);

        $response = $this->putJson('/api/profile', [
            'password' => 'newpassword123',
            'password_confirmation' => 'newpassword123'
        ]);

        $response->assertStatus(200);
        $response->assertJsonFragment([
            'message' => 'Profile updated successfully'
        ]);
        
        // Check that the password was hashed and updated
        $this->assertDatabaseHas('users', [
            'id' => $user->id
        ]);
        
        // Verify the password was updated by trying to login
        $this->assertTrue(\Hash::check('newpassword123', $user->fresh()->password));
    }
}