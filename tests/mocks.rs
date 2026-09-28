use super::*;

pub fn mock_pool() -> Pool {
    Pool {
        accumulated_rewards_per_share: 0,
        // ... other fields
    }
}

pub fn mock_user() -> User {
    User {
        pending_rewards: 0,
        // ... other fields
    }
}
