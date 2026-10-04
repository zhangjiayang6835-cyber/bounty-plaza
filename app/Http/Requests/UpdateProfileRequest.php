<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class UpdateProfileRequest extends FormRequest
{
    /**
     * Determine if the user is authorized to make this request.
     *
     * @return bool
     */
    public function authorize()
    {
        return true;
    }

    /**
     * Get the validation rules that apply to the request.
     *
     * @return array
     */
    public function rules()
    {
        return [
            'name' => ['sometimes', 'string', 'max:255'],
            'email' => ['sometimes', 'string', 'email', 'max:255', Rule::unique('users')->ignore($this->user()->id)],
            'password' => ['sometimes', 'string', 'min:8', 'confirmed'],
            'avatar' => ['sometimes', 'string', 'url'],
            'bio' => ['sometimes', 'string', 'max:500'],
            'preferences' => ['sometimes', 'array'],
            'preferences.theme' => ['sometimes', 'string', 'in:light,dark'],
            'preferences.language' => ['sometimes', 'string', 'in:en,zh,es'],
            // Add other allowed profile fields here
        ];
    }

    /**
     * Get the error messages for the defined validation rules.
     *
     * @return array
     */
    public function messages()
    {
        return [
            'name.string' => 'The name must be a string.',
            'email.email' => 'The email must be a valid email address.',
            'password.min' => 'The password must be at least 8 characters.',
            'preferences.theme.in' => 'The theme must be either light or dark.',
            'preferences.language.in' => 'The language must be one of: en, zh, es.',
        ];
    }
}