"""
Instagram scraper using the free instaloader library.
"""
import logging
from app.scrapers.utils import extract_instagram_username_from_url, generate_instagram_usernames

logger = logging.getLogger(__name__)


def scrape_instagram(business_name, website_instagram_url=None):
    """
    Attempt to retrieve public Instagram profile data for a business.

    Strategy:
    1. Use the URL found on the website (if any).
    2. Otherwise, try generated username candidates.

    Returns a dict with profile data, or None if nothing found.
    """
    try:
        import instaloader
    except ImportError:
        logger.error("instaloader is not installed. Run: pip install instaloader")
        return None

    loader = instaloader.Instaloader()

    # Build list of usernames to try
    usernames_to_try = []

    if website_instagram_url:
        parsed = extract_instagram_username_from_url(website_instagram_url)
        if parsed:
            usernames_to_try.append(parsed)

    if not usernames_to_try:
        usernames_to_try = generate_instagram_usernames(business_name)

    for username in usernames_to_try:
        try:
            profile = instaloader.Profile.from_username(loader.context, username)
            engagement_rate = _calculate_engagement(profile)
            return {
                "username": profile.username,
                "followers": profile.followers,
                "following": profile.followees,
                "posts": profile.mediacount,
                "engagement_rate": engagement_rate,
                "bio": profile.biography,
                "is_verified": profile.is_verified,
                "is_business": profile.is_business_account,
            }
        except instaloader.exceptions.ProfileNotExistsException:
            logger.debug("Instagram profile not found: %s", username)
        except instaloader.exceptions.ConnectionException as exc:
            logger.warning("Instagram connection error for %s: %s", username, exc)
        except Exception as exc:
            logger.warning("Instagram error for %s: %s", username, exc)

    return None


def _calculate_engagement(profile):
    """
    Calculate engagement rate from the last 12 posts.

    engagement_rate = (avg_likes + avg_comments) / followers * 100
    """
    if not profile.followers:
        return 0.0

    try:
        posts = profile.get_posts()
        likes_list = []
        comments_list = []
        for i, post in enumerate(posts):
            if i >= 12:
                break
            likes_list.append(post.likes)
            comments_list.append(post.comments)

        if not likes_list:
            return 0.0

        avg_likes = sum(likes_list) / len(likes_list)
        avg_comments = sum(comments_list) / len(comments_list)
        return round((avg_likes + avg_comments) / profile.followers * 100, 2)
    except Exception as exc:
        logger.warning("Error calculating engagement rate: %s", exc)
        return 0.0
