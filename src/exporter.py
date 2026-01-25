"""Export categorized repos to Markdown and update README files."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import CategorizedRepos, Repository, Category

logger = logging.getLogger(__name__)


# Placeholder tags for README integration
START_TAG = "<!-- STARRED_REPOS_START -->"
END_TAG = "<!-- STARRED_REPOS_END -->"


class MarkdownExporter:
    """Export categorized repositories to Markdown format."""
    
    def __init__(
        self,
        show_stars: bool = True,
        show_language: bool = True,
        show_description: bool = True,
        max_description_length: int = 100,
        sort_by: str = "stars",  # stars, name, starred_at
    ):
        """
        Initialize the exporter.
        
        Args:
            show_stars: Show star count
            show_language: Show programming language
            show_description: Show repo description
            max_description_length: Truncate descriptions
            sort_by: How to sort repos within categories
        """
        self.show_stars = show_stars
        self.show_language = show_language
        self.show_description = show_description
        self.max_description_length = max_description_length
        self.sort_by = sort_by
    
    def _sort_repos(self, repos: list[Repository]) -> list[Repository]:
        """Sort repositories based on configured sort order."""
        if self.sort_by == "stars":
            return sorted(repos, key=lambda r: r.stars, reverse=True)
        elif self.sort_by == "name":
            return sorted(repos, key=lambda r: r.full_name.lower())
        elif self.sort_by == "starred_at":
            return sorted(
                repos,
                key=lambda r: r.starred_at or datetime.min,
                reverse=True
            )
        return repos
    
    def _format_repo(self, repo: Repository, include_description: bool = True) -> str:
        """Format a single repository entry."""
        parts = [f"[{repo.full_name}]({repo.url})"]
        
        if self.show_language and repo.language:
            parts.append(f"`{repo.language}`")
        
        if self.show_stars:
            parts.append(f"⭐ {repo.stars:,}")
        
        if include_description and self.show_description and repo.description:
            desc = repo.description[:self.max_description_length]
            if len(repo.description) > self.max_description_length:
                desc += "..."
            parts.append(f"- {desc}")
        
        # Always include "- " prefix for proper markdown list rendering
        return f"- {' '.join(parts)}"
    
    def _format_category(
        self,
        category: Category,
        repos_limit: Optional[int] = None,
        include_description: bool = True,
    ) -> list[str]:
        """Format a category and its repos."""
        lines = []
        
        # Category header
        lines.append(f"### {category.name}")
        if category.description:
            lines.append(f"*{category.description}*")
        lines.append("")
        
        # Sort and limit repos
        repos = self._sort_repos(category.repos)
        if repos_limit:
            repos = repos[:repos_limit]
        
        # Format repos
        for repo in repos:
            lines.append(self._format_repo(repo, include_description))
        
        # Show truncation notice
        if repos_limit and len(category.repos) > repos_limit:
            remaining = len(category.repos) - repos_limit
            lines.append(f"- *...and {remaining} more*")
        
        lines.append("")
        return lines
    
    def _generate_toc(self, categories: list[Category]) -> list[str]:
        """Generate table of contents."""
        lines = ["### 📑 Table of Contents", ""]
        
        for cat in categories:
            if cat.count > 0:
                # Create anchor from category name
                anchor = cat.name.lower()
                anchor = re.sub(r'[^\w\s-]', '', anchor)
                anchor = re.sub(r'\s+', '-', anchor.strip())
                lines.append(f"- [{cat.name}](#{anchor}) ({cat.count})")
        
        lines.append("")
        return lines
    
    def generate(
        self,
        categorized: CategorizedRepos,
        title: str = "⭐ My Starred Repositories",
        include_toc: bool = True,
        include_stats: bool = True,
        include_timestamp: bool = True,
        include_description: bool = True,
        max_repos_per_category: Optional[int] = None,
        max_categories: Optional[int] = None,
        link_to_full: Optional[str] = None,
    ) -> str:
        """
        Generate Markdown document.
        
        Args:
            categorized: Categorized repositories
            title: Document title (None to skip title)
            include_toc: Include table of contents
            include_stats: Include statistics section
            include_timestamp: Include generation timestamp
            include_description: Include repo descriptions
            max_repos_per_category: Limit repos per category (None for all)
            max_categories: Limit number of categories (None for all)
            link_to_full: Add link to full file (e.g., "STARRED_REPOS.md")
        
        Returns:
            Markdown string
        """
        lines = []
        
        # Title
        if title:
            lines.append(f"# {title}")
            lines.append("")
        
        # Generation info
        if include_timestamp:
            lines.append(f"*Last updated: {categorized.generated_at.strftime('%Y-%m-%d %H:%M UTC')}*")
            lines.append(f"*Categorized using {categorized.llm_provider} ({categorized.llm_model})*")
            lines.append("")
        
        # Statistics
        if include_stats:
            lines.append(f"**{categorized.total_repos:,}** repositories organized into **{categorized.category_count}** categories")
            lines.append("")
        
        # Sort categories by count
        sorted_cats = sorted(
            categorized.categories.values(),
            key=lambda c: c.count,
            reverse=True
        )
        
        # Limit categories if specified
        if max_categories:
            sorted_cats = [c for c in sorted_cats if c.count > 0][:max_categories]
        else:
            sorted_cats = [c for c in sorted_cats if c.count > 0]
        
        # Table of contents
        if include_toc:
            lines.extend(self._generate_toc(sorted_cats))
            lines.append("---")
            lines.append("")
        
        # Categories
        for category in sorted_cats:
            lines.extend(self._format_category(
                category,
                repos_limit=max_repos_per_category,
                include_description=include_description,
            ))
        
        # Link to full file
        if link_to_full:
            lines.append(f"*[View all {categorized.total_repos} starred repositories →]({link_to_full})*")
            lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*Generated by [Starred](https://github.com/yourusername/starred) - AI-powered GitHub stars organizer*")
        
        return "\n".join(lines)
    
    def generate_for_readme(
        self,
        categorized: CategorizedRepos,
        max_repos: int = 50,
        max_categories: int = 10,
        include_toc: bool = False,
        include_description: bool = False,
        link_to_full: str = "STARRED_REPOS.md",
    ) -> str:
        """
        Generate a compact version suitable for embedding in README.
        
        This is a convenience wrapper around generate() with README-friendly defaults.
        
        Args:
            categorized: Categorized repositories
            max_repos: Maximum total repos to show
            max_categories: Maximum categories to show
            include_toc: Include table of contents
            include_description: Include repo descriptions
            link_to_full: Link to full starred repos file
        
        Returns:
            Markdown string (without main title)
        """
        # Calculate repos per category to stay under max_repos
        non_empty_cats = sum(1 for c in categorized.categories.values() if c.count > 0)
        cats_to_show = min(max_categories, non_empty_cats)
        repos_per_cat = max(max_repos // cats_to_show, 3) if cats_to_show > 0 else 5
        
        return self.generate(
            categorized,
            title=None,  # No title for README embed
            include_toc=include_toc,
            include_stats=False,
            include_timestamp=False,
            include_description=include_description,
            max_repos_per_category=repos_per_cat,
            max_categories=max_categories,
            link_to_full=link_to_full,
        )


def export_to_file(
    categorized: CategorizedRepos,
    output_path: str | Path,
    **kwargs,
) -> Path:
    """
    Export categorized repos to a Markdown file.
    
    Args:
        categorized: Categorized repositories
        output_path: Output file path
        **kwargs: Arguments passed to MarkdownExporter.generate()
    
    Returns:
        Path to the created file
    """
    output_path = Path(output_path)
    exporter = MarkdownExporter()
    
    content = exporter.generate(categorized, **kwargs)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    
    logger.info(f"Exported to {output_path}")
    return output_path


def export_to_json(
    categorized: CategorizedRepos,
    output_path: str | Path,
) -> Path:
    """
    Export categorized repos to JSON.
    
    Args:
        categorized: Categorized repositories
        output_path: Output file path
    
    Returns:
        Path to the created file
    """
    output_path = Path(output_path)
    
    data = categorized.to_dict()
    
    # Also include full repo data
    data["repositories"] = {}
    for cat in categorized.categories.values():
        for repo in cat.repos:
            data["repositories"][repo.full_name] = repo.to_dict()
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    
    logger.info(f"Exported JSON to {output_path}")
    return output_path


def update_readme(
    readme_path: str | Path,
    categorized: CategorizedRepos,
    max_repos: int = 50,
    max_categories: int = 10,
    include_toc: bool = False,
    include_description: bool = False,
    create_if_missing: bool = False,
) -> bool:
    """
    Update a README file with starred repos content between placeholder tags.
    
    The README should contain these tags:
    <!-- STARRED_REPOS_START -->
    (content will be replaced here)
    <!-- STARRED_REPOS_END -->
    
    Args:
        readme_path: Path to README file
        categorized: Categorized repositories
        max_repos: Maximum repos to show
        max_categories: Maximum categories to show
        include_toc: Include table of contents
        include_description: Include repo descriptions
        create_if_missing: Create README with placeholders if missing
    
    Returns:
        True if updated successfully
    """
    readme_path = Path(readme_path)
    
    # Generate content
    exporter = MarkdownExporter()
    content = exporter.generate_for_readme(
        categorized,
        max_repos=max_repos,
        max_categories=max_categories,
        include_toc=include_toc,
        include_description=include_description,
    )
    
    # Read existing README or create template
    if readme_path.exists():
        readme_content = readme_path.read_text(encoding="utf-8")
    elif create_if_missing:
        readme_content = f"""# My Profile

{START_TAG}
<!-- Starred repos will be inserted here -->
{END_TAG}
"""
        logger.info(f"Creating new README at {readme_path}")
    else:
        logger.error(f"README not found: {readme_path}")
        return False
    
    # Check for placeholder tags
    if START_TAG not in readme_content or END_TAG not in readme_content:
        logger.error(
            f"README does not contain placeholder tags. "
            f"Add these tags where you want starred repos:\n"
            f"{START_TAG}\n{END_TAG}"
        )
        return False
    
    # Replace content between tags using string methods (avoids regex escaping issues)
    start_idx = readme_content.find(START_TAG)
    end_idx = readme_content.find(END_TAG) + len(END_TAG)
    
    if start_idx == -1 or end_idx == -1:
        logger.error("Could not find placeholder tags positions")
        return False
    
    replacement = f"{START_TAG}\n\n{content}\n\n{END_TAG}"
    new_content = readme_content[:start_idx] + replacement + readme_content[end_idx:]
    
    # Write updated README
    readme_path.write_text(new_content, encoding="utf-8")
    logger.info(f"Updated README at {readme_path}")
    
    return True


def create_placeholder_readme(output_path: str | Path) -> Path:
    """
    Create a template README with placeholder tags.
    
    Args:
        output_path: Path for the new README
    
    Returns:
        Path to the created file
    """
    output_path = Path(output_path)
    
    template = f"""# Hi there! 👋

Welcome to my GitHub profile!

## ⭐ My Starred Repositories

{START_TAG}
<!-- This section is auto-updated by Starred -->
<!-- See: https://github.com/yourusername/starred -->

*Run the starred action to populate this section.*
{END_TAG}

## 📫 How to reach me

- Twitter: [@yourhandle](https://twitter.com/yourhandle)
- LinkedIn: [Your Name](https://linkedin.com/in/yourprofile)

---

*Profile README updated by [Starred](https://github.com/yourusername/starred)*
"""
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template, encoding="utf-8")
    
    logger.info(f"Created template README at {output_path}")
    return output_path