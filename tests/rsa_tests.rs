<content>
use super::rsa::RSAOracle;
use hex;

#[test]
fn test_rsa_oaep_decryption() {
    let oracle = RSAOracle::new(2048).expect("Failed to create RSA oracle");
    
    // Test with valid ciphertext
    let plaintext = b"Hello, world!";
    let mut rng = openssl::rand::rand::ThreadRng::new();
    let ciphertext = oracle.rsa.public_key_encrypt(
        plaintext,
        Padding::PKCS1_OAEP,
        &mut rng,
    ).expect("Failed to encrypt");
    
    let decrypted = oracle.decrypt(&ciphertext);
    assert!(decrypted.is_ok());
    assert_eq!(decrypted.unwrap(), plaintext);
    
    // Test with invalid ciphertext - should return same error
    let invalid_ciphertext = vec![0u8; 256];
    let error1 = oracle.decrypt(&invalid_ciphertext).unwrap_err();
    
    // Test with another invalid ciphertext - should return same error
    let invalid_ciphertext2 = vec![1u8; 256];
    let error2 = oracle.decrypt(&invalid_ciphertext2).unwrap_err();
    
    // Errors should be indistinguishable
    assert_eq!(format!("{}", error1), format!("{}", error2));
}

#[test]
fn test_constant_time_decryption() {
    let oracle = RSAOracle::new(2048).expect("Failed to create RSA oracle");
    
    // Create two different ciphertexts that will fail decryption
    let invalid1 = vec![0u8; 256];
    let invalid2 = vec![1u8; 256];
    
    // Time the decryption of both
    let start = std::time::Instant::now();
    let _ = oracle.decrypt(&invalid1);
    let duration1 = start.elapsed();
    
    let start = std::time::Instant::now();
    let _ = oracle.decrypt(&invalid2);
    let duration2 = start.elapsed();
    
    // The difference should be minimal (within noise margin)
    // This is a rough test - in practice you'd want more sophisticated timing tests
    assert!((duration1.as_nanos() as i64 - duration2.as_nanos() as i64).abs() < 1000000);
}

#[test]
fn test_bleichenbacher_resistance() {
    let oracle = RSAOracle::new(2048).expect("Failed to create RSA oracle");
    
    // Test vectors for Bleichenbacher attack resistance
    // These are crafted ciphertexts that would normally reveal info in a vulnerable implementation
    
    // Ciphertext with invalid padding
    let bad_padding = vec![0u8; 256];
    let result = oracle.decrypt(&bad_padding);
    assert!(result.is_err());
    
    // Ciphertext with malformed OAEP
    let malformed_oaep = vec![1u8; 256];
    let result = oracle.decrypt(&malformed_oaep);
    assert!(result.is_err());
    
    // All errors should be identical
    assert_eq!(format!("{:?}", result.unwrap_err()), "InvalidPadding");
}
</content>