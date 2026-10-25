// additional.test.ts
// ---------------------------------------------------------------
// Additional test suite for uncovered functions and methods.
// This file is intended to be placed in the project's test directory
// and run with Jest (or any compatible test runner).
// ---------------------------------------------------------------

import { describe, test, expect } from '@jest/globals';

// ==== Mocked imports (replace with real module paths) ====
import {
    parseJSON,
    stringifyJSON,
    JSONParseError,
} from '@/parsers/json';

import {
    parseBSON,
    serializeBSON,
    BSONParseError,
} from '@/parsers/bson';

import {
    parseCBOR,
    encodeCBOR,
    CBORParseError,
} from '@/parsers/cbor';

import {
    sha256,
    hmacSHA256,
    generateRandomBytes,
    CryptoError,
} from '@/crypto';

import {
    LinkedList,
    BinaryTree,
    Heap,
    DataStructureError,
} from '@/datastructures';

import {
    readFileSync,
    writeFileSync,
    FileSystemError,
} from '@/system/fs';

import {
    httpGet,
    httpPost,
    NetworkError,
} from '@/network/http';

// ---------------------------------------------------------------
// Helper utilities
// ---------------------------------------------------------------
function randomString(length: number): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; ++i) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}

// ---------------------------------------------------------------
// JSON Parser Tests
// ---------------------------------------------------------------
describe('JSON Parser', () => {
    test('parse valid JSON string', () => {
        const obj = { a: 1, b: 'text', c: [true, false, null] };
        const json = stringifyJSON(obj);
        const parsed = parseJSON(json);
        expect(parsed).toEqual(obj);
    });

    test('throw on invalid JSON', () => {
        const invalid = '{ a: 1, }';
        expect(() => parseJSON(invalid)).toThrow(JSONParseError);
    });
});

// ---------------------------------------------------------------
// BSON Parser Tests
// ---------------------------------------------------------------
describe('BSON Parser', () => {
    test('serialize and parse BSON correctly', () => {
        const data = { name: 'Bob', age: 30, tags: ['dev', 'test'] };
        const buffer = serializeBSON(data);
        const parsed = parseBSON(buffer);
        expect(parsed).toEqual(data);
    });

    test('throw on malformed BSON buffer', () => {
        const malformed = Buffer.from([0x01, 0x02, 0x03]); // too short
        expect(() => parseBSON(malformed)).toThrow(BSONParseError);
    });
});

// ---------------------------------------------------------------
// CBOR Parser Tests
// ---------------------------------------------------------------
describe('CBOR Parser', () => {
    test('encode and decode CBOR data', () => {
        const payload = { id: 12345, active: true, meta: { foo: 'bar' } };
        const encoded = encodeCBOR(payload);
        const decoded = parseCBOR(encoded);
        expect(decoded).toEqual(payload);
    });

    test('detect invalid CBOR data', () => {
        const invalid = Uint8Array.from([0xff, 0x00, 0x01]); // random bytes
        expect(() => parseCBOR(invalid)).toThrow(CBORParseError);
    });
});

// ---------------------------------------------------------------
// Cryptographic Functions Tests
// ---------------------------------------------------------------
describe('Cryptographic Utilities', () => {
    test('SHA-256 produces correct hash', () => {
        const msg = 'The quick brown fox jumps over the lazy dog';
        const expected =
            'd7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb7625e6c5b8f7e5b5b0';
        expect(sha256(msg)).toBe(expected);
    });

    test('HMAC-SHA256 matches known vector', () => {
        const key = 'key';
        const data = 'The quick brown fox jumps over the lazy dog';
        const expected =
            'f7bc83f430538424b13298e6aa6fb143ef4d59a1494618cb7f0c8e5c5b9c5c6b';
        expect(hmacSHA256(key, data)).toBe(expected);
    });

    test('generateRandomBytes returns correct length', () => {
        const len = 32;
        const bytes = generateRandomBytes(len);
        expect(bytes).toBeInstanceOf(Uint8Array);
        expect(bytes.length).toBe(len);
    });

    test('crypto functions throw on invalid input', () => {
        // @ts-expect-error intentionally passing wrong type
        expect(() => sha256(123)).toThrow(CryptoError);
    });
});

// ---------------------------------------------------------------
// Data Structures Tests
// ---------------------------------------------------------------
describe('Data Structures', () => {
    test('LinkedList basic operations', () => {
        const list = new LinkedList<number>();
        list.append(1);
        list.append(2);
        list.prepend(0);
        expect([...list]).toEqual([0, 1, 2]);
        expect(list.size()).toBe(3);
        list.remove(1);
        expect([...list]).toEqual([0, 2]);
    });

    test('BinaryTree insertion and traversal', () => {
        const tree = new BinaryTree<number>();
        [5, 3, 7, 2, 4, 6, 8].forEach(v => tree.insert(v));
        const inorder = tree.traverseInOrder();
        expect(inorder).toEqual([2, 3, 4, 5, 6, 7, 8]);
    });

    test('Heap maintains max-heap property', () => {
        const heap = new Heap<number>((a, b) => a > b); // max-heap
        [3, 1, 6, 5, 2, 4].forEach(v => heap.push(v));
        const sorted = [];
        while (!heap.isEmpty()) sorted.push(heap.pop());
        expect(sorted).toEqual([6, 5, 4, 3, 2, 1]);
    });

    test('Data structures throw on illegal operations', () => {
        const emptyList = new LinkedList<string>();
        expect(() => emptyList.remove('x')).toThrow(DataStructureError);
    });
});

// ---------------------------------------------------------------
// File System Module Tests
// ---------------------------------------------------------------
describe('File System Module', () => {
    const testFile = './tmp_test_file.txt';
    const content = randomString(64);

    afterAll(() => {
        try {
            // Cleanup
            // eslint-disable-next-line @typescript-eslint/no-var-requires
            const fs = require('fs');
            if (fs.existsSync(testFile)) fs.unlinkSync(testFile);
        } catch (_) {}
    });

    test('writeFileSync and readFileSync round‑trip', () => {
        writeFileSync(testFile, content);
        const read = readFileSync(testFile, 'utf8');
        expect(read).toBe(content);
    });

    test('readFileSync throws on missing file', () => {
        expect(() => readFileSync('./non_existent_file.txt')).toThrow(
            FileSystemError
        );
    });
});

// ---------------------------------------------------------------
// Network Module Tests (using fetch mock)
// ---------------------------------------------------------------
describe('Network Module', () => {
    // Simple fetch mock
    const globalAny: any = global;
    beforeAll(() => {
        globalAny.fetch = jest.fn((url: string, opts: any) => {
            if (url.includes('success')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ status: 'ok' }),
                    text: () => Promise.resolve('ok'),
                });
            }
            return Promise.resolve({
                ok: false,
                status: 500,
                statusText: 'Internal Server Error',
                json: () => Promise.resolve({ error: 'fail' }),
                text: () => Promise.resolve('fail'),
            });
        });
    });

    test('httpGet resolves on successful response', async () => {
        const resp = await httpGet('https://example.com/success');
        expect(resp).toEqual({ status: 'ok' });
    });

    test('httpGet rejects on error status', async () => {
        await expect(httpGet('https://example.com/fail')).rejects.toThrow(
            NetworkError
        );
    });

    test('httpPost sends payload and receives response', async () => {
        const payload = { foo: 'bar' };
        const resp = await httpPost('https://example.com/success', payload);
        expect(resp).toEqual({ status: 'ok' });
        expect(globalAny.fetch).toHaveBeenCalledWith(
            'https://example.com/success',
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify(payload),
                headers: expect.any(Object),
            })
        );
    });
});