#!/usr/bin/env python3
"""
Test script to verify marker removal is working end-to-end
"""
import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'LLM_calls'))

from LLM_calls.together_get_response import clean_response

# Test cases
test_cases = [
    ("Hello world", "Hello world"),
    ("Hello world <|end|>", "Hello world"),
    ("Hello <|end|> world", "Hello world"),
    ("Hello [END FINAL RESPONSE] garbage", "Hello"),
    ("Hello world [END FINAL RESPONSE] <|end|> ignore this", "Hello world"),
    ("<|end|> Hello world", "Hello world"),
    ("  Hello   world  ", "Hello world"),
    ("Hello\n\nworld", "Hello world"),
    ("CLEAN TEST [END FINAL RESPONSE] <|end|> REMOVE THIS", "CLEAN TEST"),
    ("Multiple <|end|> markers <|end|> removed", "Multiple markers removed"),
]

print("=" * 70)
print("MARKER REMOVAL TEST SUITE")
print("=" * 70)

passed = 0
failed = 0

for i, (input_text, expected) in enumerate(test_cases, 1):
    result = clean_response(input_text)
    status = "✓ PASS" if result == expected else "✗ FAIL"
    
    if result == expected:
        passed += 1
        print(f"\n[{i}] {status}")
    else:
        failed += 1
        print(f"\n[{i}] {status}")
        print(f"    Input:    {repr(input_text)}")
        print(f"    Expected: {repr(expected)}")
        print(f"    Got:      {repr(result)}")

print("\n" + "=" * 70)
print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print("=" * 70)

if failed == 0:
    print("\n✓ All marker removal tests passed!")
    sys.exit(0)
else:
    print(f"\n✗ {failed} test(s) failed")
    sys.exit(1)
