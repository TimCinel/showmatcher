#!/usr/bin/env python3
"""
YAML-based test suite for showmatcher that validates renaming logic without actually moving files.
Uses test_cases.yaml to define test configurations and expected outputs.
All test data is driven from the YAML configuration file.
"""

import os
import re
import sys
import unittest
import yaml
from unittest.mock import patch, MagicMock


class MatcherLogic:
    """Extracted logic from matcher.py for testing without file operations"""
    
    @staticmethod
    def filename_filter(filename):
        """Filter filename characters for filesystem compatibility"""
        return re.sub('[:<>/|?*\\\\]', '-', filename)
    
    @staticmethod
    def process_pattern_match(basename_noext, naming_pattern, series_name):
        """Process a file using pattern matching logic"""
        pattern_match = re.compile(naming_pattern).search(basename_noext)
        
        if not pattern_match:
            return None
            
        # Extract season, episode, and name from pattern with proper group checking
        try:
            season = int(pattern_match.group('season')) if pattern_match.group('season') else 1
        except IndexError:
            season = 1
        
        try:
            episode = int(pattern_match.group('episode')) if pattern_match.group('episode') else 1
        except IndexError:
            episode = 1
        
        try:
            name = pattern_match.group('name').strip() if pattern_match.group('name') else ''
        except IndexError:
            name = ''
        
        return {
            'season': season,
            'episode': episode,
            'name': name,
            'series_name': series_name
        }
    
    @staticmethod
    def generate_output_path(episode_info, file_extension):
        """Generate the expected output path based on episode info"""
        if not episode_info:
            return None
            
        series_name = MatcherLogic.filename_filter(episode_info['series_name'])
        episode_name = MatcherLogic.filename_filter(episode_info['name'])
        
        if episode_name:
            episode_name = f" {episode_name}"
        
        # Check if we have episode number info
        if 'airedEpisodeNumber' in episode_info:
            full_name = "{} S{:0>2d}E{:0>2d}{}".format(
                series_name,
                episode_info['airedSeason'],
                episode_info['airedEpisodeNumber'],
                episode_name
            )
            nice_path = os.path.join("Season {:0>2d}".format(episode_info['airedSeason']), full_name)
        else:
            full_name = "{} S{:0>2d}E{:0>2d}{}".format(
                series_name,
                episode_info['season'],
                episode_info['episode'],
                episode_name
            )
            nice_path = os.path.join("Season {:0>2d}".format(episode_info['season']), full_name)
        
        return f"{nice_path}{file_extension}"


class TestYamlMatcher(unittest.TestCase):
    """YAML-based test cases for showmatcher functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = os.path.dirname(__file__)
        self.yaml_file = os.path.join(self.test_dir, 'test_cases.yaml')
        self.maxDiff = None  # Show full diff for assertions
        
        # Load YAML test configuration
        with open(self.yaml_file, 'r') as f:
            self.test_config = yaml.safe_load(f)
    
    def test_yaml_file_loads(self):
        """Test that the YAML file loads correctly"""
        self.assertIsNotNone(self.test_config)
        self.assertIn('test_suites', self.test_config)
        self.assertGreater(len(self.test_config['test_suites']), 0)
    
    def test_all_yaml_test_cases(self):
        """Run all test cases defined in the YAML file"""
        for suite in self.test_config['test_suites']:
            with self.subTest(suite=suite['name']):
                self._run_test_suite(suite)
    
    def _run_test_suite(self, suite):
        """Run a single test suite from the YAML configuration"""
        config = suite['config']
        tests = suite['tests']
        
        for i, test_case in enumerate(tests):
            # Handle both single files and lists for subTest context
            input_files = test_case['in']
            if isinstance(input_files, str):
                context_desc = input_files
            else:
                context_desc = f"{len(input_files)} files: {input_files[0]}..."
            
            with self.subTest(test_index=i, input_files=context_desc):
                self._run_single_test(config, test_case)
    
    def _run_single_test(self, config, test_case):
        """Run a single test case - handles both single files and file lists"""
        input_files = test_case['in']
        expected_outputs = test_case['out']
        
        # Normalize to lists for consistent processing
        if isinstance(input_files, str):
            input_files = [input_files]
        if isinstance(expected_outputs, str):
            expected_outputs = [expected_outputs]
        
        # Ensure we have the same number of inputs and outputs
        self.assertEqual(
            len(input_files), 
            len(expected_outputs), 
            f"Input/output count mismatch: {len(input_files)} inputs, {len(expected_outputs)} outputs"
        )
        
        # The primary file (first .mp4 file, or first file if no .mp4) determines the episode info
        primary_file = None
        for file_path in input_files:
            if file_path.endswith('.mp4'):
                primary_file = file_path
                break
        
        # If no .mp4 file found, use the first file (handles standalone sidecar files)
        if primary_file is None:
            primary_file = input_files[0]
        
        # Extract episode info from primary file
        basename_noext = os.path.splitext(os.path.basename(primary_file))[0]
        episode_info = MatcherLogic.process_pattern_match(
            basename_noext, 
            config['naming-pattern'], 
            config['series-name']
        )
        
        if episode_info is None:
            self.fail(f"Failed to match pattern for: {primary_file}\n"
                     f"  Basename: {basename_noext}\n"
                     f"  Pattern: {config['naming-pattern']}")
        
        # Process each file and compare with expected output
        for i, (input_path, expected_output) in enumerate(zip(input_files, expected_outputs)):
            file_extension = os.path.splitext(input_path)[1]
            actual_output = MatcherLogic.generate_output_path(episode_info, file_extension)
            
            self.assertEqual(
                actual_output, 
                expected_output, 
                f"Output mismatch for file {i+1}/{len(input_files)} ({input_path}):\n"
                f"  Expected: {expected_output}\n"
                f"  Actual:   {actual_output}\n"
                f"  Episode info: {episode_info}"
            )
    
    def test_character_filtering(self):
        """Test filename character filtering using YAML data"""
        if 'character_filter_tests' not in self.test_config:
            self.skipTest("No character_filter_tests found in YAML")
        
        for test_case in self.test_config['character_filter_tests']:
            with self.subTest(input=test_case['input']):
                result = MatcherLogic.filename_filter(test_case['input'])
                self.assertEqual(
                    result, 
                    test_case['expected'], 
                    f"Character filtering failed for: {test_case['input']}"
                )
    
    def test_pattern_validation(self):
        """Test pattern validation cases using YAML data"""
        if 'pattern_validation_tests' not in self.test_config:
            self.skipTest("No pattern_validation_tests found in YAML")
        
        for test_case in self.test_config['pattern_validation_tests']:
            with self.subTest(description=test_case['description']):
                episode_info = MatcherLogic.process_pattern_match(
                    test_case['input'],
                    test_case['pattern'],
                    test_case['series']
                )
                
                if test_case['should_match']:
                    self.assertIsNotNone(episode_info, f"Pattern should match: {test_case['input']}")
                    
                    # Check expected values if provided
                    if 'expected_season' in test_case:
                        self.assertEqual(episode_info['season'], test_case['expected_season'])
                    if 'expected_episode' in test_case:
                        self.assertEqual(episode_info['episode'], test_case['expected_episode'])
                    if 'expected_name' in test_case:
                        self.assertEqual(episode_info['name'], test_case['expected_name'])
                else:
                    self.assertIsNone(episode_info, f"Pattern should not match: {test_case['input']}")
    
    def test_multi_file_processing(self):
        """Test that multi-file test cases work correctly"""
        # Find a multi-file test case in the YAML
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
        
        self.assertIsNotNone(multi_file_test, "No multi-file test case found in YAML")
        
        # Test that the multi-file test has consistent input/output counts
        input_files = multi_file_test['in']
        output_files = multi_file_test['out']
        
        self.assertEqual(len(input_files), len(output_files), 
                        "Multi-file test should have equal input/output counts")
        
        # Test that all files share the same base name (different extensions)
        primary_basename = os.path.splitext(os.path.basename(input_files[0]))[0]
        for input_file in input_files[1:]:
            test_basename = os.path.splitext(os.path.basename(input_file))[0]
            self.assertEqual(primary_basename, test_basename,
                           f"All files should share same basename: {primary_basename} vs {test_basename}")
        
        # Test that extensions are preserved in outputs
        for input_file, output_file in zip(input_files, output_files):
            input_ext = os.path.splitext(input_file)[1]
            output_ext = os.path.splitext(output_file)[1]
            self.assertEqual(input_ext, output_ext, 
                           f"Extension should be preserved: {input_ext} -> {output_ext}")
    
    def test_yaml_structure_completeness(self):
        """Test that all required YAML sections are present"""
        # Validate main structure
        self.assertIn('test_suites', self.test_config)
        self.assertIsInstance(self.test_config['test_suites'], list)
        
        # Validate each test suite structure
        for i, suite in enumerate(self.test_config['test_suites']):
            with self.subTest(suite_index=i, suite_name=suite.get('name', f'Suite {i}')):
                self.assertIn('name', suite, f"Suite {i} missing 'name'")
                self.assertIn('config', suite, f"Suite {i} missing 'config'")
                self.assertIn('tests', suite, f"Suite {i} missing 'tests'")
                
                # Validate config structure
                config = suite['config']
                required_config_keys = ['destination', 'series-name', 'naming-pattern', 'directory']
                for key in required_config_keys:
                    self.assertIn(key, config, f"Suite {i} config missing '{key}'")
                
                # Validate test structure
                tests = suite['tests']
                self.assertIsInstance(tests, list, f"Suite {i} tests should be a list")
                
                for j, test in enumerate(tests):
                    self.assertIn('in', test, f"Suite {i}, test {j} missing 'in'")
                    self.assertIn('out', test, f"Suite {i}, test {j} missing 'out'")


class YamlTestRunner:
    """Test runner for YAML-based tests"""
    
    def __init__(self, yaml_file_path):
        self.yaml_file_path = yaml_file_path
    
    def run_all_tests(self):
        """Run all YAML-based tests"""
        suite = unittest.TestSuite()
        
        # Add all test methods
        suite.addTest(TestYamlMatcher('test_yaml_file_loads'))
        suite.addTest(TestYamlMatcher('test_all_yaml_test_cases'))
        suite.addTest(TestYamlMatcher('test_character_filtering'))
        suite.addTest(TestYamlMatcher('test_pattern_validation'))
        suite.addTest(TestYamlMatcher('test_multi_file_processing'))
        suite.addTest(TestYamlMatcher('test_yaml_structure_completeness'))
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    
    def validate_yaml_structure(self):
        """Validate the YAML file structure"""
        try:
            with open(self.yaml_file_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if 'test_suites' not in config:
                print("❌ YAML file missing 'test_suites' key")
                return False
            
            for i, suite in enumerate(config['test_suites']):
                if 'name' not in suite:
                    print(f"❌ Test suite {i} missing 'name'")
                    return False
                if 'config' not in suite:
                    print(f"❌ Test suite {i} missing 'config'")
                    return False
                if 'tests' not in suite:
                    print(f"❌ Test suite {i} missing 'tests'")
                    return False
                
                for j, test in enumerate(suite['tests']):
                    if 'in' not in test:
                        print(f"❌ Test suite {i}, test {j} missing 'in'")
                        return False
                    if 'out' not in test:
                        print(f"❌ Test suite {i}, test {j} missing 'out'")
                        return False
            
            print("✅ YAML structure validation passed")
            return True
            
        except yaml.YAMLError as e:
            print(f"❌ YAML parsing error: {e}")
            return False
        except FileNotFoundError:
            print(f"❌ YAML file not found: {self.yaml_file_path}")
            return False


if __name__ == '__main__':
    # First validate YAML structure
    yaml_file = os.path.join(os.path.dirname(__file__), 'test_cases.yaml')
    runner = YamlTestRunner(yaml_file)
    
    if not runner.validate_yaml_structure():
        sys.exit(1)
    
    # Run the tests
    success = runner.run_all_tests()
    
    if success:
        print("\n✅ All YAML-based tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some YAML-based tests failed!")
        sys.exit(1)