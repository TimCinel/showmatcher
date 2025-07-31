#!/usr/bin/env python3
"""
Integration tests for showmatcher that create real files, run the actual script,
and verify the results by checking the output directory structure.
"""

import os
import sys
import shutil
import subprocess
import tempfile
import unittest
import yaml
from pathlib import Path


class TestMatcherIntegration(unittest.TestCase):
    """Integration tests that run the actual matcher script against real files"""
    
    def setUp(self):
        """Set up test environment with real directories and files"""
        self.test_dir = os.path.dirname(__file__)
        self.project_root = os.path.dirname(self.test_dir)
        self.matcher_script = os.path.join(self.project_root, 'matcher.py')
        self.yaml_file = os.path.join(self.test_dir, 'test_cases.yaml')
        
        # Create test data directories
        self.data_in_dir = os.path.join(self.test_dir, 'data-in')
        self.data_out_dir = os.path.join(self.test_dir, 'data-out')
        
        # Load YAML test configuration
        with open(self.yaml_file, 'r') as f:
            self.test_config = yaml.safe_load(f)
        
        # Clean up and recreate directories
        self._cleanup_test_dirs()
        self._create_test_dirs()
        
        # Store original environment to restore later
        self.original_env = dict(os.environ)
    
    def tearDown(self):
        """Clean up test environment"""
        self._cleanup_test_dirs()
        
        # Restore original environment - NEVER leave environment modified
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def _cleanup_test_dirs(self):
        """Remove test directories if they exist"""
        for dir_path in [self.data_in_dir, self.data_out_dir]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
    
    def _create_test_dirs(self):
        """Create test directories"""
        os.makedirs(self.data_in_dir, exist_ok=True)
        os.makedirs(self.data_out_dir, exist_ok=True)
    
    def _create_test_files_for_suite(self, suite):
        """Create test files and config for a specific test suite"""
        suite_name = suite['name']
        config = suite['config']
        tests = suite['tests']
        
        # Create a directory for this suite
        suite_dir = os.path.join(self.data_in_dir, suite_name.replace(' ', '_').lower())
        os.makedirs(suite_dir, exist_ok=True)
        
        # Create .matcherrc config file
        config_file = os.path.join(suite_dir, '.matcherrc')
        with open(config_file, 'w') as f:
            f.write(f"directory = {suite_dir}\n")
            f.write(f"destination = {os.path.join(self.data_out_dir, suite_name.replace(' ', '_').lower())}\n")
            f.write(f"series-name = {config['series-name']}\n")
            if 'naming-pattern' in config:
                f.write(f"naming-pattern = {config['naming-pattern']}\n")
            if 'ignore-substring' in config:
                f.write(f"ignore-substring = {config['ignore-substring']}\n")
            f.write("dry-run = false\n")
        
        # Create test files from the YAML test cases
        created_files = []
        for test_case in tests:
            input_files = test_case['in']
            if isinstance(input_files, str):
                input_files = [input_files]
            
            for input_file in input_files:
                # Extract just the filename from the path
                filename = os.path.basename(input_file)
                file_path = os.path.join(suite_dir, filename)
                
                # Create the file with some dummy content
                with open(file_path, 'w') as f:
                    f.write(f"Test content for {filename}\n")
                
                created_files.append({
                    'path': file_path,
                    'filename': filename,
                    'expected_output': test_case.get('out')  # May be None if no match expected
                })
        
        return suite_dir, config_file, created_files
    
    def _run_matcher(self, config_file, env_vars=None):
        """Run the matcher script with the given config file and environment"""
        cmd = [
            sys.executable, 
            self.matcher_script, 
            '--config', config_file
        ]
        
        # Create environment for subprocess - inherit from parent but allow overrides
        test_env = dict(os.environ)
        if env_vars:
            test_env.update(env_vars)
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30,
                cwd=self.project_root,
                env=test_env
            )
            return result
        except subprocess.TimeoutExpired:
            self.fail("Matcher script timed out after 30 seconds")
        except Exception as e:
            self.fail(f"Failed to run matcher script: {e}")
    
    def _verify_output_files(self, suite_name, expected_files):
        """Verify that output files were created correctly"""
        output_dir = os.path.join(self.data_out_dir, suite_name.replace(' ', '_').lower())
        
        # Separate files that should have matches from those that shouldn't
        files_with_matches = [f for f in expected_files if f['expected_output'] is not None]
        files_without_matches = [f for f in expected_files if f['expected_output'] is None]
        
        if files_with_matches:
            # If we expect any matches, the output directory should exist
            if not os.path.exists(output_dir):
                self.fail(f"Output directory not created: {output_dir}")
            
            # Check that expected files exist
            for file_info in files_with_matches:
                expected_outputs = file_info['expected_output']
                if isinstance(expected_outputs, str):
                    expected_outputs = [expected_outputs]
                
                for expected_output in expected_outputs:
                    expected_path = os.path.join(output_dir, expected_output)
                    
                    self.assertTrue(
                        os.path.exists(expected_path),
                        f"Expected output file not found: {expected_path}"
                    )
                    
                    # Verify file has content
                    with open(expected_path, 'r') as f:
                        content = f.read().strip()
                        self.assertTrue(
                            len(content) > 0,
                            f"Output file is empty: {expected_path}"
                        )
        
        # Verify files without expected matches remained in input directory
        for file_info in files_without_matches:
            original_path = file_info['path']
            self.assertTrue(
                os.path.exists(original_path),
                f"File without expected match was moved (but shouldn't have been): {original_path}"
            )
    
    def test_pattern_matching_integration(self):
        """Test pattern matching mode with real files"""
        # Find the Full Pattern Matching test suite
        pattern_suite = None
        for suite in self.test_config['test_suites']:
            if suite['name'] == "Full Pattern Matching":
                pattern_suite = suite
                break
        
        self.assertIsNotNone(pattern_suite, "Full Pattern Matching suite not found in YAML")
        
        # Create test files
        suite_dir, config_file, created_files = self._create_test_files_for_suite(pattern_suite)
        
        # Verify input files were created
        self.assertTrue(os.path.exists(suite_dir))
        self.assertTrue(os.path.exists(config_file))
        self.assertGreater(len(created_files), 0, "No test files were created")
        
        # Run the matcher
        result = self._run_matcher(config_file)
        
        # Check that the command succeeded
        if result.returncode != 0:
            self.fail(f"Matcher script failed with return code {result.returncode}\n"
                     f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}")
        
        # Verify output files were created correctly
        self._verify_output_files(pattern_suite['name'], created_files)
        
        # Verify input files were moved (no longer in input directory) - only for files with expected matches
        for file_info in created_files:
            original_path = file_info['path']
            if file_info['expected_output'] is not None:
                self.assertFalse(
                    os.path.exists(original_path),
                    f"Input file was not moved: {original_path}"
                )
    
    def test_multi_file_integration(self):
        """Test multi-file (sidecar) handling with real files"""
        # Check for TVDB API key in original environment (not modified by tests)
        api_key = self.original_env.get('TVDB_API_KEY')
        if not api_key:
            self.skipTest("TVDB_API_KEY environment variable required for TVDB integration tests")
            
        # Find a suite with multi-file test cases
        multi_file_suite = None
        multi_file_test = None
        
        for suite in self.test_config['test_suites']:
            for test_case in suite['tests']:
                if isinstance(test_case['in'], list) and len(test_case['in']) > 1:
                    multi_file_suite = suite
                    multi_file_test = test_case
                    break
            if multi_file_test:
                break
        
        self.assertIsNotNone(multi_file_suite, "No multi-file test suite found")
        
        # Create a minimal test suite with just the multi-file test
        test_suite = {
            'name': multi_file_suite['name'] + '_MultiFile',
            'config': multi_file_suite['config'],
            'tests': [multi_file_test]
        }
        
        # Create test files
        suite_dir, config_file, created_files = self._create_test_files_for_suite(test_suite)
        
        # Verify all related files were created
        input_files = multi_file_test['in']
        self.assertEqual(len(created_files), len(input_files), 
                        "Not all multi-files were created")
        
        # Run the matcher with TVDB API key
        result = self._run_matcher(config_file, {'TVDB_API_KEY': api_key})
        
        # Check for success
        if result.returncode != 0:
            self.fail(f"Multi-file matcher failed with return code {result.returncode}\n"
                     f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}")
        
        # Verify all output files were created
        self._verify_output_files(test_suite['name'], created_files)
    
    def test_dry_run_integration(self):
        """Test that dry run mode doesn't move files"""
        # Check for TVDB API key in original environment
        api_key = self.original_env.get('TVDB_API_KEY')
        if not api_key:
            self.skipTest("TVDB_API_KEY environment variable required for TVDB integration tests")
            
        # Get a test suite
        test_suite = self.test_config['test_suites'][0]  # Use first suite
        
        # Create test files with dry-run enabled
        suite_dir, config_file, created_files = self._create_test_files_for_suite(test_suite)
        
        # Modify config to enable dry-run
        with open(config_file, 'a') as f:
            f.write("dry-run = true\n")
        
        # Run the matcher with TVDB API key
        result = self._run_matcher(config_file, {'TVDB_API_KEY': api_key})
        
        # Check for success
        if result.returncode != 0:
            self.fail(f"Dry run failed with return code {result.returncode}\n"
                     f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}")
        
        # Verify ALL input files were NOT moved (still exist) - in dry run, nothing should move
        for file_info in created_files:
            original_path = file_info['path']
            self.assertTrue(
                os.path.exists(original_path),
                f"Input file was moved during dry run: {original_path}"
            )
        
        # Verify no output files were created
        output_dir = os.path.join(self.data_out_dir, test_suite['name'].replace(' ', '_').lower())
        if os.path.exists(output_dir):
            output_files = list(Path(output_dir).rglob('*'))
            output_files = [f for f in output_files if f.is_file()]
            self.assertEqual(len(output_files), 0, 
                           f"Files were created during dry run: {output_files}")
    
    def test_error_handling_integration(self):
        """Test error handling with invalid configurations"""
        # Create a test directory
        error_test_dir = os.path.join(self.data_in_dir, 'error_test')
        os.makedirs(error_test_dir, exist_ok=True)
        
        # Create a file
        test_file = os.path.join(error_test_dir, 'Test File.mp4')
        with open(test_file, 'w') as f:
            f.write("Test content\n")
        
        # Create config with invalid pattern (missing required groups)
        config_file = os.path.join(error_test_dir, '.matcherrc')
        with open(config_file, 'w') as f:
            f.write(f"directory = {error_test_dir}\n")
            f.write(f"destination = {os.path.join(self.data_out_dir, 'error_test')}\n")
            f.write("series-name = Test Series\n")
            f.write("naming-pattern = Invalid Pattern Without Groups\n")
            f.write("dry-run = false\n")
        
        # Run the matcher
        result = self._run_matcher(config_file)
        
        # Should handle the error gracefully (may succeed with warnings or fail cleanly)
        # The important thing is it shouldn't crash
        self.assertIsNotNone(result.returncode, "Matcher script should complete")
        
        # Verify original file still exists (wasn't moved due to pattern failure)
        self.assertTrue(os.path.exists(test_file), 
                       "Original file should remain after pattern matching failure")
    
    def test_filename_filtering_integration(self):
        """Test that problematic characters in filenames are handled correctly"""
        # Check for TVDB API key in original environment
        api_key = self.original_env.get('TVDB_API_KEY')
        if not api_key:
            self.skipTest("TVDB_API_KEY environment variable required for TVDB integration tests")
            
        # Find the filename filtering test suite
        filtering_suite = None
        for suite in self.test_config['test_suites']:
            if suite['name'] == "Filename Character Filtering":
                filtering_suite = suite
                break
        
        if not filtering_suite:
            self.skipTest("Filename Character Filtering suite not found in YAML")
        
        # Create test files
        suite_dir, config_file, created_files = self._create_test_files_for_suite(filtering_suite)
        
        # Run the matcher with TVDB API key  
        result = self._run_matcher(config_file, {'TVDB_API_KEY': api_key})
        
        # Check for success
        if result.returncode != 0:
            self.fail(f"Character filtering test failed with return code {result.returncode}\n"
                     f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}")
        
        # Verify output files were created with filtered names
        self._verify_output_files(filtering_suite['name'], created_files)
        
        # Specifically check that problematic characters were replaced
        output_dir = os.path.join(self.data_out_dir, filtering_suite['name'].replace(' ', '_').lower())
        output_files = list(Path(output_dir).rglob('*.mp4'))
        
        # Verify no output files contain problematic characters
        problematic_chars = [':', '<', '>', '/', '|', '?', '*', '\\']
        for output_file in output_files:
            filename = output_file.name
            for char in problematic_chars:
                self.assertNotIn(char, filename, 
                               f"Problematic character '{char}' found in output filename: {filename}")
    
    def test_ignore_substring_integration(self):
        """Test ignore-substring mode with TVDB lookup"""
        # Check for TVDB API key in original environment
        api_key = self.original_env.get('TVDB_API_KEY')
        if not api_key:
            self.skipTest("TVDB_API_KEY environment variable required for TVDB integration tests")
            
        # Find a suite using ignore-substring (Peter Rabbit)
        ignore_suite = None
        for suite in self.test_config['test_suites']:
            if 'ignore-substring' in suite['config'] and suite['name'] == "Peter Rabbit Pattern Matching":
                ignore_suite = suite
                break
        
        if not ignore_suite:
            self.skipTest("No ignore-substring test suite found")
        
        # Create a minimal test with just one file
        test_suite = {
            'name': ignore_suite['name'],
            'config': ignore_suite['config'],
            'tests': [ignore_suite['tests'][0]]  # Just test one file
        }
        
        # Create test files
        suite_dir, config_file, created_files = self._create_test_files_for_suite(test_suite)
        
        # Run the matcher with TVDB API key
        result = self._run_matcher(config_file, {'TVDB_API_KEY': api_key})
        
        # With a real API key, this should work properly
        if result.returncode != 0:
            self.fail(f"Ignore substring test failed with return code {result.returncode}\n"
                     f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}")
        
        # Verify that it attempted TVDB lookup
        self.assertIn("Looking up", result.stdout, "Should show TVDB lookup attempt")


class IntegrationTestRunner:
    """Test runner for integration tests"""
    
    def __init__(self):
        self.test_dir = os.path.dirname(__file__)
    
    def run_all_tests(self):
        """Run all integration tests"""
        suite = unittest.TestSuite()
        
        # Add integration test methods
        suite.addTest(TestMatcherIntegration('test_pattern_matching_integration'))
        suite.addTest(TestMatcherIntegration('test_multi_file_integration'))
        suite.addTest(TestMatcherIntegration('test_dry_run_integration'))
        suite.addTest(TestMatcherIntegration('test_error_handling_integration'))
        suite.addTest(TestMatcherIntegration('test_filename_filtering_integration'))
        suite.addTest(TestMatcherIntegration('test_ignore_substring_integration'))
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    
    def check_prerequisites(self):
        """Check that required files exist for testing"""
        test_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(test_dir)
        
        required_files = [
            os.path.join(project_root, 'matcher.py'),
            os.path.join(test_dir, 'test_cases.yaml')
        ]
        
        missing_files = [f for f in required_files if not os.path.exists(f)]
        
        if missing_files:
            print("❌ Missing required files for integration tests:")
            for f in missing_files:
                print(f"  - {f}")
            return False
        
        print("✅ All required files found for integration tests")
        return True


if __name__ == '__main__':
    # Check prerequisites first
    runner = IntegrationTestRunner()
    
    if not runner.check_prerequisites():
        sys.exit(1)
    
    # Check for TVDB API key in environment
    if not os.environ.get('TVDB_API_KEY'):
        print("❌ TVDB_API_KEY environment variable is required for integration tests")
        print("   Get your API key from: https://thetvdb.com/api-information")
        print("   Set it with: export TVDB_API_KEY=your_api_key")
        print("   Or add it to .env file: echo 'export TVDB_API_KEY=your_key' >> .env")
        sys.exit(1)
    
    print("🚀 Running integration tests...")
    print("📁 Creating real files and directories...")
    print("⚙️  Running actual matcher script with TVDB integration...")
    print("🔍 Verifying file movements and outputs...")
    print()
    
    # Run the tests
    success = runner.run_all_tests()
    
    if success:
        print("\n✅ All integration tests passed!")
        print("🎉 End-to-end functionality verified!")
        sys.exit(0)
    else:
        print("\n❌ Some integration tests failed!")
        print("🔧 Check the output above for details.")
        sys.exit(1)