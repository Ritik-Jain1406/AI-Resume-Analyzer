"""
matching/learning_resources.py
----------------------------------
Static data for Phase 6: a curated map of skill -> (resource name, URL)
pointing to each technology's official documentation or primary learning
hub, plus category-level time estimates and priority weighting used by
skill_gap.py.

Kept as data (not fetched at runtime) so recommendations are instant and
don't depend on network access or web search. Soft skills don't have a
single canonical doc site, so they fall back to a constructed Coursera
search link rather than a guessed article URL.
"""

from __future__ import annotations

# skill name (must match data/skills.csv exactly) -> (resource name, URL)
LEARNING_RESOURCES: dict[str, tuple[str, str]] = {
    # Programming
    "Python": ("Python Official Tutorial", "https://docs.python.org/3/tutorial/"),
    "Java": ("Oracle Java Tutorials", "https://docs.oracle.com/javase/tutorial/"),
    "C++": ("learncpp.com", "https://www.learncpp.com/"),
    "C": ("Learn-C.org", "https://www.learn-c.org/"),
    "C#": ("Microsoft Learn — C#", "https://learn.microsoft.com/en-us/dotnet/csharp/"),
    "JavaScript": ("MDN JavaScript Guide", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide"),
    "TypeScript": ("TypeScript Handbook", "https://www.typescriptlang.org/docs/handbook/intro.html"),
    "Go": ("A Tour of Go", "https://go.dev/tour/"),
    "Rust": ("The Rust Book", "https://doc.rust-lang.org/book/"),
    "Ruby": ("Ruby Official Documentation", "https://www.ruby-lang.org/en/documentation/"),
    "PHP": ("PHP Manual", "https://www.php.net/manual/en/"),
    "Swift": ("Swift.org Documentation", "https://www.swift.org/documentation/"),
    "Kotlin": ("Kotlin Docs", "https://kotlinlang.org/docs/home.html"),
    "R": ("R for Data Science", "https://r4ds.hadley.nz/"),
    "MATLAB": ("MathWorks MATLAB Documentation", "https://www.mathworks.com/help/matlab/"),
    "SQL": ("W3Schools SQL Tutorial", "https://www.w3schools.com/sql/"),
    "Scala": ("Scala Documentation", "https://docs.scala-lang.org/"),
    "Bash": ("GNU Bash Manual", "https://www.gnu.org/software/bash/manual/bash.html"),
    "HTML": ("MDN HTML Guide", "https://developer.mozilla.org/en-US/docs/Web/HTML"),
    "CSS": ("MDN CSS Guide", "https://developer.mozilla.org/en-US/docs/Web/CSS"),

    # Frameworks
    "Django": ("Django Official Documentation", "https://docs.djangoproject.com/en/stable/"),
    "Flask": ("Flask Documentation", "https://flask.palletsprojects.com/"),
    "FastAPI": ("FastAPI Documentation", "https://fastapi.tiangolo.com/"),
    "React": ("React Official Docs", "https://react.dev/learn"),
    "Angular": ("Angular Documentation", "https://angular.dev/"),
    "Vue.js": ("Vue.js Guide", "https://vuejs.org/guide/introduction.html"),
    "Node.js": ("Node.js Documentation", "https://nodejs.org/en/docs"),
    "Express.js": ("Express.js Guide", "https://expressjs.com/en/starter/installing.html"),
    "Spring Boot": ("Spring Boot Docs", "https://spring.io/projects/spring-boot"),
    ".NET": ("Microsoft .NET Docs", "https://learn.microsoft.com/en-us/dotnet/"),
    "Ruby on Rails": ("Rails Guides", "https://guides.rubyonrails.org/"),
    "Next.js": ("Next.js Documentation", "https://nextjs.org/docs"),
    "TensorFlow": ("TensorFlow Tutorials", "https://www.tensorflow.org/tutorials"),
    "PyTorch": ("PyTorch Tutorials", "https://pytorch.org/tutorials/"),
    "Keras": ("Keras Getting Started", "https://keras.io/getting_started/"),
    "Scikit-learn": ("Scikit-learn Getting Started", "https://scikit-learn.org/stable/getting_started.html"),
    "Pandas": ("Pandas Getting Started", "https://pandas.pydata.org/docs/getting_started/index.html"),
    "NumPy": ("NumPy Quickstart", "https://numpy.org/doc/stable/user/quickstart.html"),
    "Bootstrap": ("Bootstrap Docs", "https://getbootstrap.com/docs/"),
    "Tailwind CSS": ("Tailwind CSS Docs", "https://tailwindcss.com/docs"),

    # Cloud
    "AWS": ("AWS Getting Started", "https://aws.amazon.com/getting-started/"),
    "Azure": ("Microsoft Azure Docs", "https://learn.microsoft.com/en-us/azure/"),
    "GCP": ("Google Cloud Docs", "https://cloud.google.com/docs"),
    "Heroku": ("Heroku Dev Center", "https://devcenter.heroku.com/"),
    "DigitalOcean": ("DigitalOcean Tutorials", "https://www.digitalocean.com/community/tutorials"),
    "Firebase": ("Firebase Docs", "https://firebase.google.com/docs"),
    "Vercel": ("Vercel Docs", "https://vercel.com/docs"),
    "Netlify": ("Netlify Docs", "https://docs.netlify.com/"),

    # Databases
    "MySQL": ("MySQL Reference Manual", "https://dev.mysql.com/doc/"),
    "PostgreSQL": ("PostgreSQL Documentation", "https://www.postgresql.org/docs/"),
    "MongoDB": ("MongoDB Docs", "https://www.mongodb.com/docs/"),
    "SQLite": ("SQLite Documentation", "https://www.sqlite.org/docs.html"),
    "Redis": ("Redis Docs", "https://redis.io/docs/"),
    "Oracle": ("Oracle Database Docs", "https://docs.oracle.com/en/database/"),
    "Cassandra": ("Apache Cassandra Docs", "https://cassandra.apache.org/doc/latest/"),
    "DynamoDB": ("AWS DynamoDB Docs", "https://docs.aws.amazon.com/dynamodb/"),
    "Elasticsearch": ("Elastic Guide", "https://www.elastic.co/guide/index.html"),
    "MariaDB": ("MariaDB Knowledge Base", "https://mariadb.com/kb/en/documentation/"),

    # Developer Tools
    "Git": ("Git Documentation", "https://git-scm.com/doc"),
    "GitHub": ("GitHub Docs", "https://docs.github.com/"),
    "GitLab": ("GitLab Docs", "https://docs.gitlab.com/"),
    "Docker": ("Docker Get Started", "https://docs.docker.com/get-started/"),
    "Kubernetes": ("Kubernetes Docs", "https://kubernetes.io/docs/home/"),
    "Jenkins": ("Jenkins Docs", "https://www.jenkins.io/doc/"),
    "CI/CD": ("GitLab CI/CD Docs", "https://docs.gitlab.com/ee/ci/"),
    "Postman": ("Postman Learning Center", "https://learning.postman.com/"),
    "Jira": ("Atlassian Jira Docs", "https://support.atlassian.com/jira-software-cloud/"),
    "VS Code": ("VS Code Docs", "https://code.visualstudio.com/docs"),
    "Linux": ("Linux Journey", "https://linuxjourney.com/"),
    "Nginx": ("Nginx Docs", "https://nginx.org/en/docs/"),
    "Terraform": ("Terraform Docs", "https://developer.hashicorp.com/terraform/docs"),
    "Ansible": ("Ansible Docs", "https://docs.ansible.com/"),
}

# Categories treated as core technical skills (weighted highest for priority)
CORE_CATEGORIES: frozenset[str] = frozenset({"Programming", "Frameworks", "Databases"})
# Categories treated as secondary technical skills
SECONDARY_CATEGORIES: frozenset[str] = frozenset({"Cloud", "Developer Tools"})

# category -> (min_weeks, max_weeks) to learn working proficiency from scratch.
# Soft Skills are intentionally excluded — see format_time_estimate().
CATEGORY_TIME_WEEKS: dict[str, tuple[int, int]] = {
    "Programming": (4, 8),
    "Frameworks": (2, 4),
    "Cloud": (3, 6),
    "Databases": (1, 3),
    "Developer Tools": (1, 2),
}

DEFAULT_TIME_WEEKS: tuple[int, int] = (2, 4)


def get_resource(skill: str, category: str) -> tuple[str, str]:
    """Return (resource_name, url) for a skill, falling back to a search link."""
    if skill in LEARNING_RESOURCES:
        return LEARNING_RESOURCES[skill]
    query = skill.replace(" ", "+")
    return (
        f"Search Coursera for {skill}",
        f"https://www.coursera.org/search?query={query}",
    )


def format_time_estimate(category: str) -> str:
    """Return a human-readable estimated learning time for a skill's category."""
    if category == "Soft Skills":
        return "Ongoing practice"
    lo, hi = CATEGORY_TIME_WEEKS.get(category, DEFAULT_TIME_WEEKS)
    return f"{lo}-{hi} weeks"
