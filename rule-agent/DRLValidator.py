#
#    Copyright 2024 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
import os
import tempfile
import subprocess
import json
from typing import Dict, Optional, Tuple

class DRLValidator:
    """
    Self-healing DRL validator that uses LLM to fix compilation errors.

    This class attempts to compile Drools DRL rules and, if compilation fails,
    uses an LLM to iteratively fix syntax errors until the rules compile successfully
    or the maximum number of attempts is reached.
    """

    def __init__(self, llm):
        """
        Initialize the DRL validator.

        Args:
            llm: Language model instance for fixing DRL syntax errors
        """
        self.llm = llm

    def validate_and_fix_drl(self, drl_content: str, schema: Dict, bank_id: str,
                             policy_type: str, max_attempts: int = 3) -> Tuple[bool, str, str]:
        """
        Validate DRL syntax and automatically fix errors using LLM.

        Args:
            drl_content: The DRL rules content to validate
            schema: The schema definition for the rules
            bank_id: Bank identifier
            policy_type: Policy type identifier
            max_attempts: Maximum number of fix attempts (default: 3)

        Returns:
            Tuple of (success: bool, final_drl: str, message: str)
        """
        print("\n" + "="*80)
        print("DRL VALIDATION AND SELF-HEALING")
        print("="*80)

        current_drl = drl_content

        for attempt in range(1, max_attempts + 1):
            print(f"\n--- Validation Attempt {attempt}/{max_attempts} ---")

            # Attempt compilation
            is_valid, error_message = self._compile_drl(current_drl, bank_id, policy_type)

            if is_valid:
                print("✓ DRL compilation successful!")
                if attempt > 1:
                    print(f"✓ Rules fixed after {attempt - 1} attempt(s)")
                return True, current_drl, "DRL validated successfully"

            print(f"✗ Compilation failed with error:\n{error_message}")

            # If this was the last attempt, return failure
            if attempt == max_attempts:
                error_msg = f"Failed to fix DRL after {max_attempts} attempts. Last error: {error_message}"
                print(f"\n✗ {error_msg}")
                return False, current_drl, error_msg

            # Use LLM to fix the DRL
            print(f"\n→ Attempting to fix DRL using LLM (attempt {attempt}/{max_attempts - 1})...")
            fixed_drl = self._fix_drl_with_llm(current_drl, error_message, schema)

            if not fixed_drl or fixed_drl == current_drl:
                error_msg = f"LLM could not generate a fix for the DRL errors"
                print(f"✗ {error_msg}")
                return False, current_drl, error_msg

            current_drl = fixed_drl
            print("→ LLM generated a fix, retrying compilation...")

        return False, current_drl, "Unexpected validation flow completion"

    def _compile_drl(self, drl_content: str, bank_id: str, policy_type: str) -> Tuple[bool, str]:
        """
        Attempt to compile DRL content using KIE Maven plugin.

        Args:
            drl_content: The DRL content to compile
            bank_id: Bank identifier
            policy_type: Policy type identifier

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        # Create a temporary directory for the Maven project
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Maven project structure
            src_main_resources = os.path.join(temp_dir, "src", "main", "resources", "rules")
            os.makedirs(src_main_resources, exist_ok=True)

            # Write DRL file
            drl_file = os.path.join(src_main_resources, "rules.drl")
            with open(drl_file, 'w', encoding='utf-8') as f:
                f.write(drl_content)

            # Create pom.xml
            pom_content = self._generate_pom_xml(bank_id, policy_type)
            pom_file = os.path.join(temp_dir, "pom.xml")
            with open(pom_file, 'w', encoding='utf-8') as f:
                f.write(pom_content)

            # Run Maven compile
            try:
                result = subprocess.run(
                    ["mvn", "clean", "compile"],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minute timeout
                )

                if result.returncode == 0:
                    return True, ""
                else:
                    # Extract relevant error messages from Maven output
                    error_msg = self._extract_compilation_errors(result.stdout + "\n" + result.stderr)
                    return False, error_msg

            except subprocess.TimeoutExpired:
                return False, "Compilation timeout after 2 minutes"
            except FileNotFoundError:
                # Maven not available, fall back to basic syntax check
                print("⚠ Maven not found, performing basic DRL syntax validation...")
                return self._basic_drl_validation(drl_content)
            except Exception as e:
                return False, f"Compilation error: {str(e)}"

    def _basic_drl_validation(self, drl_content: str) -> Tuple[bool, str]:
        """
        Perform basic DRL syntax validation when Maven is not available.

        Args:
            drl_content: The DRL content to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        errors = []

        # Check for basic DRL structure
        if "package " not in drl_content:
            errors.append("Missing 'package' declaration")

        if "rule " not in drl_content:
            errors.append("No rules found in DRL content")

        # Check for common syntax errors
        lines = drl_content.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()

            # Check for unmatched braces
            if line.startswith("rule "):
                if "when" not in drl_content[drl_content.find(line):]:
                    errors.append(f"Line {i}: Rule missing 'when' clause")
                if "then" not in drl_content[drl_content.find(line):]:
                    errors.append(f"Line {i}: Rule missing 'then' clause")

        if errors:
            return False, "\n".join(errors)

        return True, ""

    def _extract_compilation_errors(self, maven_output: str) -> str:
        """
        Extract relevant compilation error messages from Maven output.

        Args:
            maven_output: Full Maven command output

        Returns:
            Formatted error message string
        """
        errors = []
        lines = maven_output.split('\n')

        capture_error = False
        for line in lines:
            # Look for error markers
            if '[ERROR]' in line or 'Rule Compilation error' in line or 'Unable to Analyse Expression' in line:
                capture_error = True
                errors.append(line)
            elif capture_error and line.strip():
                errors.append(line)
                # Stop capturing after a few lines
                if len(errors) > 20:
                    break
            elif capture_error and not line.strip():
                # Empty line might end the error block
                if len(errors) > 5:
                    break

        if errors:
            return '\n'.join(errors[:30])  # Limit to first 30 lines

        return maven_output[-2000:]  # Return last 2000 chars if no specific errors found

    def _generate_pom_xml(self, bank_id: str, policy_type: str) -> str:
        """
        Generate Maven pom.xml for DRL compilation.

        Args:
            bank_id: Bank identifier
            policy_type: Policy type identifier

        Returns:
            pom.xml content as string
        """
        artifact_id = f"{bank_id}-{policy_type}-rules-validation"

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example.rules</groupId>
    <artifactId>{artifact_id}</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>

    <properties>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <drools.version>7.74.1.Final</drools.version>
        <maven.compiler.source>1.8</maven.compiler.source>
        <maven.compiler.target>1.8</maven.compiler.target>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.drools</groupId>
            <artifactId>drools-core</artifactId>
            <version>${{drools.version}}</version>
        </dependency>
        <dependency>
            <groupId>org.drools</groupId>
            <artifactId>drools-compiler</artifactId>
            <version>${{drools.version}}</version>
        </dependency>
        <dependency>
            <groupId>org.kie</groupId>
            <artifactId>kie-api</artifactId>
            <version>${{drools.version}}</version>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.kie</groupId>
                <artifactId>kie-maven-plugin</artifactId>
                <version>${{drools.version}}</version>
                <extensions>true</extensions>
            </plugin>
        </plugins>
    </build>
</project>"""

    def _fix_drl_with_llm(self, drl_content: str, error_message: str, schema: Dict) -> Optional[str]:
        """
        Use LLM to fix DRL compilation errors.

        Args:
            drl_content: The current DRL content with errors
            error_message: The compilation error message
            schema: The schema definition for reference

        Returns:
            Fixed DRL content, or None if LLM could not fix it
        """
        schema_str = json.dumps(schema, indent=2)

        prompt = f"""You are a Drools DRL syntax expert. A DRL rule file failed to compile with the following error:

ERROR:
{error_message}

CURRENT DRL CONTENT:
{drl_content}

SCHEMA DEFINITION:
{schema_str}

Please fix the DRL syntax errors. Common issues to check:

1. **Variable declarations must reference declared fact types**:
   - WRONG: `$smoking : smoking` or `$age : age` or `$health : health`
   - CORRECT: `$applicant : Applicant($smoking : smoker)` or `$applicant : Applicant(age < 18)`
   - To extract a field value into a variable, bind to the object first, then extract: `$applicant : Applicant($smoking : smoker)`
   - Then use `$smoking` in the then clause: `int points = $smoking ? 5 : 0;`

2. **Field access must use valid object references**:
   - Variables must bind to objects from declare statements (Applicant, Policy, Decision, etc.)
   - Fields are accessed via the object: `$applicant.smoker`, `$policy.coverageAmount`

3. **CRITICAL: Field Ownership - Access fields from the correct object type**:
   - Applicant fields (age, creditScore, annualIncome, health, smoker, debtToIncome, etc.) MUST be accessed from Applicant
   - Policy fields (loanType, coverageAmount, term, interestRate, policyType, minimumLoanAmount, maximumLoanAmount, etc.) MUST be accessed from Policy
   - WRONG: `$applicant : Applicant(loanType == "personal")` - loanType is NOT on Applicant!
   - CORRECT: `$applicant : Applicant(...) $policy : Policy(loanType == "personal")`
   - If you see "unable to resolve method Applicant.loanType()" or similar, the field is on the wrong object type

4. **Never create variables from primitive field names**:
   - Fields like 'smoker', 'age', 'income', 'smoking', 'health' are properties of objects, not standalone types
   - WRONG: `$smoking : smoking` - 'smoking' is not a type, it's a field
   - CORRECT: `$applicant : Applicant($smoking : smoker)` - bind to Applicant first, then extract smoker field
   - Always bind to the parent object first, then extract the field value
   - Common mistake: `$smoking : smoking` should be `$applicant : Applicant($smoking : smoker)`

5. **All conditions must be properly formed with parentheses**

6. **Check that all field names match the schema exactly**

7. **CRITICAL: Type Conversion for accumulate() results**:
   - The `accumulate()` function returns a `Long` or `BigDecimal`, NOT an `int` or `double`
   - If you see errors like "The method setTotalPoints(int) is not applicable for the arguments (Long)", you MUST convert:
   - WRONG: `rc.setTotalPoints($total);` where `$total` comes from `accumulate(..., $total : sum(...))`
   - CORRECT: `int total = $total.intValue(); rc.setTotalPoints(total);`
   - For sum operations: ALWAYS use `int total = $total.intValue();` before calling setters that expect int
   - For count operations: ALWAYS use `int count = $count.intValue();` before calling setters that expect int
   - For average operations: ALWAYS use `double avg = $avg.doubleValue();` before calling setters that expect double
   - Pattern: Extract accumulate result → Convert to primitive → Use converted value in setter

Return ONLY the corrected DRL content, with no explanations or markdown formatting. The response should start with 'package' and contain the complete, valid DRL file."""

        try:
            response = self.llm.invoke(prompt)

            # Extract content from response
            if hasattr(response, 'content'):
                fixed_drl = response.content.strip()
            else:
                fixed_drl = str(response).strip()

            # Remove markdown code blocks if present
            if fixed_drl.startswith('```'):
                lines = fixed_drl.split('\n')
                # Remove first line (```) and last line (```)
                if lines[-1].strip() == '```':
                    lines = lines[1:-1]
                else:
                    lines = lines[1:]
                # Remove language identifier if present
                if lines and lines[0].strip() in ['drl', 'java', 'drools']:
                    lines = lines[1:]
                fixed_drl = '\n'.join(lines)

            # Validate the response starts with package declaration
            if not fixed_drl.startswith('package '):
                print("⚠ LLM response does not start with 'package', attempting to extract...")
                # Try to find package declaration
                package_idx = fixed_drl.find('package ')
                if package_idx >= 0:
                    fixed_drl = fixed_drl[package_idx:]
                else:
                    print("✗ Could not find valid DRL content in LLM response")
                    return None

            return fixed_drl

        except Exception as e:
            print(f"✗ Error invoking LLM for DRL fix: {str(e)}")
            return None
