from django.conf import settings


PAGE_SEARCH_METADATA = {
    "website:home": {
        "title": "City College of Bayawan | Official Website",
        "description": (
            "Official website of City College of Bayawan. Find academic programs, "
            "admission requirements, campus news, student resources, and downloads."
        ),
    },
    "website:about": {
        "title": "About City College of Bayawan | Mission and Campus",
        "description": (
            "Learn about City College of Bayawan, its mission, vision, leadership, "
            "and commitment to accessible higher education in Bayawan City."
        ),
    },
    "website:admissions": {
        "title": "Admissions | City College of Bayawan",
        "description": (
            "View City College of Bayawan admission requirements, application guidance, "
            "and official information for prospective students."
        ),
    },
    "website:academics": {
        "title": "Academic Programs | City College of Bayawan",
        "description": (
            "Explore the academic programs and course information available at City "
            "College of Bayawan in Bayawan City, Negros Oriental."
        ),
    },
    "website:faculty": {
        "title": "Faculty and Staff | City College of Bayawan",
        "description": (
            "Meet the faculty, staff, and academic leaders serving the City College of "
            "Bayawan community."
        ),
    },
    "website:students": {
        "title": "Student Resources | City College of Bayawan",
        "description": (
            "Access official student resources, forms, services, and campus information "
            "from City College of Bayawan."
        ),
    },
    "website:downloads": {
        "title": "Forms and Downloads | City College of Bayawan",
        "description": (
            "Download official City College of Bayawan forms, documents, guides, and "
            "other campus resources."
        ),
    },
    "website:news": {
        "title": "Campus News and Events | City College of Bayawan",
        "description": (
            "Read official City College of Bayawan announcements, campus news, events, "
            "and student updates."
        ),
    },
    "website:contact": {
        "title": "Contact City College of Bayawan",
        "description": (
            "Contact City College of Bayawan for questions about admissions, academics, "
            "student services, and other campus concerns."
        ),
    },
}

DEFAULT_SEARCH_METADATA = {
    "title": "City College of Bayawan | Official Website",
    "description": (
        "Official website of City College of Bayawan in Bayawan City, Negros Oriental, "
        "Philippines."
    ),
}


def search_metadata(request):
    site_url = settings.PUBLIC_SITE_URL.rstrip("/")
    view_name = request.resolver_match.view_name if request.resolver_match else ""
    metadata = PAGE_SEARCH_METADATA.get(view_name, DEFAULT_SEARCH_METADATA)
    return {
        "public_site_url": site_url,
        "canonical_url": f"{site_url}{request.path}",
        "is_public_homepage": view_name == "website:home",
        "seo_title": metadata["title"],
        "seo_description": metadata["description"],
        "seo_image_url": f"{site_url}{settings.STATIC_URL}images/hero-images/ccb-logo.png",
    }
