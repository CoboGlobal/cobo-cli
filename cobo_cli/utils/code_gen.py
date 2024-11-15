import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ProcessContext(BaseModel):
    """Context information for file processing"""

    app_type: str
    wallet_type: str
    auth: str

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get value from context"""
        return getattr(self, key, default)


class Rule:
    """Class representing a single rule"""

    def __init__(self, rule_list: List[Dict[str, Any]]):
        self.rule_list = self._normalize_rules(rule_list)

    def _normalize_rules(
        self, rule_list: List[Dict[str, Any]]
    ) -> List[Dict[str, List[str]]]:
        """Normalize the rule list"""
        normalized = []
        for rule_dict in rule_list:
            norm_dict = {}
            for key, value in rule_dict.items():
                if isinstance(value, str):
                    norm_dict[key] = [value]
                elif isinstance(value, list):
                    norm_dict[key] = value
                elif isinstance(value, dict):
                    # Handle nested dictionaries
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, list):
                            norm_dict[sub_key] = sub_value
                        else:
                            norm_dict[sub_key] = [sub_value]
                else:
                    raise ValueError(f"Invalid rule value type: {type(value)}")
            normalized.append(norm_dict)
        return normalized

    def evaluate(self, context: ProcessContext) -> bool:
        """Evaluate if rules are satisfied (all rules must be satisfied)"""
        if not self.rule_list:
            return True

        # All rules must be satisfied
        for rule_dict in self.rule_list:
            if not self._evaluate_single_rule(rule_dict, context):
                return False
        return True

    def _evaluate_single_rule(
        self, rule_dict: Dict[str, List[str]], context: ProcessContext
    ) -> bool:
        """Evaluate a single rule dictionary"""
        for key, expected_values in rule_dict.items():
            current_value = context.get(key)
            if current_value is None:
                return False

            # Skip this condition if expected values list is empty
            if not expected_values:
                continue

            matched = False
            for value in expected_values:
                is_negation = isinstance(value, str) and value.startswith("!")
                if is_negation:
                    if current_value != value[1:]:
                        matched = True
                        break
                else:
                    if current_value == value:
                        matched = True
                        break

            if not matched:
                return False

        return True


class CodeGen:
    """Main code generator class"""

    def __init__(self, code_gen_file: Optional[Union[str, Path]] = None):
        """Initialize code generator

        Args:
            code_gen_file: Path to .code_gen.yaml file
        """
        self.code_gen_file = Path(code_gen_file) if code_gen_file else None
        self.rules: Dict[str, Rule] = {}
        self._load_rules()

    def _load_rules(self) -> None:
        """Load rules from .code_gen.yaml file"""
        if not self.code_gen_file or not self.code_gen_file.exists():
            logger.debug(f"No rules file found at {self.code_gen_file}")
            return

        try:
            with self.code_gen_file.open("r") as f:
                raw_rules = yaml.safe_load(f) or {}

            for pattern, rule_list in raw_rules.items():
                if not isinstance(rule_list, list):
                    raise ValueError(f"Rules for {pattern} must be a list")
                self.rules[pattern] = Rule(rule_list)
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            raise

    def process(self, path: Union[str, Path], context: ProcessContext) -> None:
        """Process a file or directory

        Args:
            path: Path to file or directory to process
            context: Processing context
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        # Get path relative to working directory
        try:
            relative_path = path.relative_to(path.parent)
        except ValueError:
            relative_path = path

        if path.is_file():
            if self.should_process_file(str(relative_path), context):
                self._process_file(path, context)
            else:
                logger.info(f"Removing file: {path}")
                path.unlink()
        else:
            self._process_directory(path, context)

    def _process_directory(self, directory: Path, context: ProcessContext) -> None:
        """Process a directory"""
        to_remove = set()
        to_process = set()
        skip_paths = set()

        # Collect files to process and remove
        for root, dirs, files in os.walk(directory, topdown=True):
            root_path = Path(root)
            relative_root = root_path.relative_to(directory)

            # Check if current directory should be removed
            if str(relative_root) != ".":
                folder_path = str(relative_root) + "/"
                if not self.should_process_file(folder_path, context):
                    to_remove.add(root_path)
                    skip_paths.add(str(relative_root))
                    dirs.clear()
                    continue

            # Check if parent directory is marked for removal
            if any(
                str(relative_root).startswith(skip_path) for skip_path in skip_paths
            ):
                dirs.clear()
                continue

            for file in files:
                file_path = root_path / file
                relative_path = file_path.relative_to(directory)

                if any(
                    str(relative_path).startswith(skip_path) for skip_path in skip_paths
                ):
                    continue

                if self.should_process_file(str(relative_path), context):
                    to_process.add(file_path)
                else:
                    to_remove.add(file_path)

        # Execute removals (starting from deepest paths)
        sorted_removes = sorted(
            to_remove, key=lambda x: str(x).count(os.sep), reverse=True
        )
        for path in sorted_removes:
            try:
                if path.is_file():
                    logger.info(f"Removing file: {path}")
                    path.unlink()
                elif path.is_dir():
                    logger.info(f"Removing directory: {path}")
                    import shutil

                    shutil.rmtree(path)
            except Exception as e:
                logger.error(f"Failed to remove {path}: {e}")

        # Process files
        for file_path in to_process:
            if file_path.exists():
                try:
                    self._process_file(file_path, context)
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")

    def should_process_file(self, file_path: str, context: ProcessContext) -> bool:
        """Determine if a file should be processed"""
        # Normalize file path
        normalized_path = str(Path(file_path))

        # Check all rules
        for pattern, rule in self.rules.items():
            if self._match_path_pattern(normalized_path, pattern):
                return rule.evaluate(context)

        # Keep file by default
        return True

    def _match_path_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches pattern"""
        # Normalize path separators
        file_path = str(Path(file_path))
        pattern = str(Path(pattern))

        # Handle directory patterns
        if pattern.endswith("/"):
            pattern = pattern[:-1]
            return file_path == pattern or file_path.startswith(pattern + os.sep)
        # Handle wildcard patterns
        elif pattern.endswith("/*"):
            dir_pattern = pattern[:-2]
            return file_path.startswith(dir_pattern + os.sep)
        # Exact match
        return file_path == pattern

    def _process_file(self, file_path: Path, context: ProcessContext) -> None:
        """Process a single file
        This method can be overridden to implement specific file processing logic
        """


class TemplateCodeGen(CodeGen):
    """Code generator with template replacement support"""

    def _process_file(self, file_path: Path, context: ProcessContext) -> None:
        """Process file using template engine"""
        try:
            # Try reading as UTF-8 to check if it's a text file
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Skip non-UTF-8 files (likely binary files)
            return
        processed_content = self.process_template(content, context)
        with open(file_path, "w") as f:
            f.write(processed_content)

    def process_template(self, content: str, context: ProcessContext) -> str:
        """Process template content"""
        lines = content.split("\n")
        processed_lines = []
        stack = [True]  # Condition stack
        for line in lines:
            if line.strip().startswith(("#")):  # Check comment lines
                if "%if" in line:
                    condition = self._parse_condition(line, context)
                    stack.append(condition and stack[-1])
                elif "%elif" in line:
                    if stack[-1]:  # Skip this block if previous condition was true
                        stack[-1] = False
                    else:
                        condition = self._parse_condition(line, context)
                        stack[-1] = condition and stack[-2]
                elif "%else" in line:
                    if len(stack) > 1:
                        stack[-1] = not stack[-1] and stack[-2]
                elif "%endif" in line:
                    if len(stack) > 1:
                        stack.pop()
            elif all(stack):  # Add line only if all conditions are true
                processed_lines.append(line)

        return "\n".join(processed_lines)

    def _parse_condition(self, line: str, context: ProcessContext) -> bool:
        """Parse condition statement"""
        condition = re.search(r"%if\s+(.+)$|%elif\s+(.+)$", line)
        if condition:
            cond = condition.group(1) or condition.group(2)
            return self._eval_condition(cond, context)
        return False

    def _eval_condition(self, condition: str, context: ProcessContext) -> bool:
        """Evaluate condition"""
        parts = condition.split()
        key = parts[0]
        op = parts[1]
        value = " ".join(parts[2:])

        if op == "==":
            return context.get(key) == value
        elif op == "!=":
            return context.get(key) != value
        elif op == "in":
            values = self._parse_list(value)
            return context.get(key) in values
        elif op == "not" and parts[2] == "in":
            values = self._parse_list(" ".join(parts[3:]))
            return context.get(key) not in values

        return False

    def _parse_list(self, value: str) -> list:
        """Parse list string"""
        value = value.strip("[]")
        return [v.strip() for v in value.split(",")]
