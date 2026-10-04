<content>
<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

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
            'name' => 'sometimes|string|max:255',
            'email' => 'sometimes|string|email|max:255|unique:users,email,' . auth()->id(),
            'password' => 'sometimes|string|min:8|confirmed',
            'avatar' => 'sometimes|image|max:2048',
            'bio' => 'sometimes|string|max:1000',
            'phone' => 'sometimes|string|max:20',
            'website' => 'sometimes|url|max:255',
        ];
    }
}