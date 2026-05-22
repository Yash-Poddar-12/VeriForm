from playwright.sync_api import sync_playwright
import random
import string
import csv
import re
from datetime import datetime

URL = "https://myaccount.bajajhousingfinance.in/#/tracker/tracker-home"


# -----------------------------
# AI-LIKE FIELD UNDERSTANDING
# -----------------------------
def detect_field_type(field_info):

    text = field_info.lower()

    if any(x in text for x in ["mobile", "phone", "contact"]):
        return "mobile"

    elif "pan" in text:
        return "pan"

    elif "loan" in text:
        return "loan"

    elif "email" in text:
        return "email"

    return "generic"


# -----------------------------
# GENERATE VALID VALUE
# -----------------------------
def generate_valid_value(field_type):

    if field_type == "mobile":
        return ''.join(random.choices("6789", k=1)) + \
               ''.join(random.choices(string.digits, k=9))

    elif field_type == "pan":
        return (
            ''.join(random.choices(string.ascii_uppercase, k=5)) +
            ''.join(random.choices(string.digits, k=4)) +
            random.choice(string.ascii_uppercase)
        )

    elif field_type == "loan":
        return "HL" + ''.join(random.choices(string.digits, k=8))

    elif field_type == "email":
        return "test" + str(random.randint(100, 999)) + "@gmail.com"

    return ''.join(random.choices(string.ascii_letters, k=8))


# -----------------------------
# GENERATE INVALID VALUE
# -----------------------------
def generate_invalid_value(field_type):

    invalid_pool = {
        "mobile": [
            "12345",
            "abcdefghij",
            "@#$%^",
            ""
        ],

        "pan": [
            "1234567890",
            "ABCDE123",
            "@@@@@1111A",
            ""
        ],

        "loan": [
            "@@@###",
            "123",
            "",
            "<script>"
        ],

        "email": [
            "invalid-email",
            "@gmail.com",
            "abc@",
            ""
        ],

        "generic": [
            "",
            "@#$%^",
            "<script>alert(1)</script>"
        ]
    }

    return random.choice(
        invalid_pool.get(field_type, invalid_pool["generic"])
    )


# -----------------------------
# MAIN TESTING
# -----------------------------
results = []

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False,
        slow_mo=700
    )

    page = browser.new_page()

    # Run multiple AI-generated iterations
    for test_no in range(1, 6):

        print(f"\n========== TEST {test_no} ==========")

        try:

            page.goto(URL, timeout=60000)

            page.wait_for_timeout(5000)

            inputs = page.locator("input")

            input_count = inputs.count()

            print(f"Detected {input_count} input fields")

            field_results = []

            # -----------------------------
            # DETECT + GENERATE INPUTS
            # -----------------------------
            for i in range(input_count):

                field = inputs.nth(i)

                try:

                    placeholder = field.get_attribute("placeholder") or ""
                    name = field.get_attribute("name") or ""
                    field_id = field.get_attribute("id") or ""
                    field_type_html = field.get_attribute("type") or ""

                    field_info = f"""
                    {placeholder}
                    {name}
                    {field_id}
                    {field_type_html}
                    """

                    detected_type = detect_field_type(field_info)

                    # Randomly choose valid or invalid
                    use_valid = random.choice([True, False])

                    if use_valid:
                        value = generate_valid_value(detected_type)
                    else:
                        value = generate_invalid_value(detected_type)

                    # Fill field
                    field.fill(value)

                    print(f"\nField {i+1}")
                    print("Detected Type:", detected_type)
                    print("Entered:", value)

                    page.wait_for_timeout(1000)

                    # Browser validation
                    validation_message = field.evaluate(
                        "(el) => el.validationMessage"
                    )

                    field_results.append({
                        "field": detected_type,
                        "value": value,
                        "validation": validation_message
                    })

                except Exception as e:
                    print("Field Error:", str(e))

            # -----------------------------
            # AUTO CLICK BUTTON
            # -----------------------------
            buttons = page.locator("button")

            submitted = False

            for b in range(buttons.count()):

                try:

                    btn = buttons.nth(b)

                    if btn.is_visible() and btn.is_enabled():

                        btn.click(timeout=3000)

                        submitted = True

                        print(f"\nClicked Button {b+1}")

                        break

                except:
                    pass

            page.wait_for_timeout(4000)

            # -----------------------------
            # DETECT ERRORS
            # -----------------------------
            page_text = page.locator("body").inner_text().lower()

            detected_errors = []

            error_keywords = [
                "invalid",
                "required",
                "incorrect",
                "error",
                "failed"
            ]

            for keyword in error_keywords:

                if keyword in page_text:
                    detected_errors.append(keyword)

            # -----------------------------
            # DETERMINE STATUS
            # -----------------------------
            status = "PASS"

            for f in field_results:

                if f["validation"]:
                    status = "FAIL"

            if detected_errors:
                status = "FAIL"

            results.append([
                test_no,
                field_results,
                detected_errors,
                status,
                page.url
            ])

            print("\nSTATUS:", status)

        except Exception as e:

            print("TEST ERROR:", str(e))

            results.append([
                test_no,
                "ERROR",
                str(e)
            ])

    # -----------------------------
    # GENERATE REPORT
    # -----------------------------
    filename = f"ai_form_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(filename, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow([
            "Test Number",
            "Field Results",
            "Detected Errors",
            "Status",
            "Final URL"
        ])

        writer.writerows(results)

    print(f"\nREPORT GENERATED: {filename}")

    page.wait_for_timeout(5000)

    browser.close()