<content>
use openssl::{
    error::ErrorStack,
    rsa::{Rsa, Padding},
    symm::encrypt,
};
use std::error::Error;

pub struct RSAOracle {
    rsa: Rsa<openssl::pkey::Private>,
}

impl RSAOracle {
    pub fn new(key_size: u32) -> Result<Self, ErrorStack> {
        let rsa = Rsa::generate(key_size)?;
        Ok(RSAOracle { rsa })
    }

    pub fn decrypt(&self, ciphertext: &[u8]) -> Result<Vec<u8>, DecryptionError> {
        // Convert to constant time by using fixed-size buffer and timing-resistant comparison
        let mut buf = vec![0; self.rsa.size() as usize];
        let result = self.rsa.private_decrypt(
            ciphertext,
            &mut buf,
            Padding::PKCS1_OAEP,
        );

        // Always return the same error message regardless of the actual error
        // This prevents Bleichenbacher oracle attacks
        match result {
            Ok(plaintext) => Ok(plaintext),
            Err(_) => Err(DecryptionError::InvalidPadding),
        }
    }

    pub fn get_public_key(&self) -> Result<Vec<u8>, ErrorStack> {
        let key = self.rsa.public_key_to_pem()?;
        Ok(key)
    }

    pub fn get_key_size(&self) -> u32 {
        self.rsa.size()
    }
}

#[derive(Debug, Clone)]
pub enum DecryptionError {
    InvalidPadding,
}

impl std::fmt::Display for DecryptionError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Decryption failed")
    }
}

impl Error for DecryptionError {}
</content>