import html

from diff_match_patch import diff_match_patch


def highlight_differences(original, corrected):
    """
    Highlights differences between original and corrected text at character level.
    Returns the corrected text with HTML highlighting for changed parts.
    Uses the diff-match-patch library for more accurate character-level diffs.
    """
    # Create a diff_match_patch object
    dmp = diff_match_patch()

    # Get the diff between the two texts
    diffs = dmp.diff_main(original, corrected)

    # Apply semantic cleanup to make the diff more meaningful
    dmp.diff_cleanupSemantic(diffs)

    # Process the diff to create HTML with highlights
    result = []
    for op, text in diffs:
        if op == 0:  # Equal
            result.append(html.escape(text))
        elif op == 1:  # Inserted
            result.append(
                f"<span style='background-color: #DCFCE7; color: #166534; font-weight: bold;'>{html.escape(text)}</span>"
            )
        elif op == -1:  # Deleted
            result.append(
                f"<span style='background-color: #FEE2E2; color: #991B1B; text-decoration: line-through;'>{html.escape(text)}</span>"
            )

    # Join the result and replace newlines with <br> for HTML display
    return "".join(result).replace("\n", "<br>")
