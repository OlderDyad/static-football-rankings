# team_links.py
"""
Modular Team Link Generation System
Used by ALL page generators to create consistent team links

Features:
- Cached database lookups for performance
- URL slug generation
- Graceful handling of missing pages
- Flexible link types (icon, full, both)

Usage:
    from team_links import get_link_generator
    
    linker = get_link_generator(SERVER, DATABASE)
    html = linker.generate_link(team_id, team_name, link_type='icon')
"""

import pyodbc
import re
from functools import lru_cache
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlugGenerator:
    """Utility to create consistent URL-safe slugs"""
    
    @staticmethod
    def create(state, city, team_name):
        """
        Generate URL slug from team components
        
        Example: create("WA", "Everett", "Seagulls") → "wa-everett-seagulls"
        """
        # Combine parts
        parts = []
        
        if state:
            parts.append(state.lower())
        if city:
            parts.append(city.lower())
        
        # Clean team name - remove state code in parentheses
        clean_name = re.sub(r'\s*\([A-Z]{2}\)\s*$', '', team_name)
        parts.append(clean_name.lower())
        
        raw = '-'.join(parts)
        
        # Remove special chars, normalize spaces
        slug = re.sub(r'[^a-z0-9\s-]', '', raw)
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'-+', '-', slug)  # Collapse multiple dashes
        slug = slug.strip('-')
        
        return slug
    
    @staticmethod
    def create_from_team_name(team_name):
        """
        Generate slug from full team name like "Everett (WA)"
        
        Example: "Everett (WA)" → "wa-everett"
        """
        # Extract state from parentheses
        state_match = re.search(r'\(([A-Z]{2})\)', team_name)
        state = state_match.group(1) if state_match else None
        
        # Remove state code
        clean_name = re.sub(r'\s*\([A-Z]{2}\)\s*$', '', team_name)
        
        # For simple names, use name + state
        if state:
            return SlugGenerator.create(state, None, clean_name)
        else:
            return SlugGenerator.create(None, None, clean_name)


class TeamLinkGenerator:
    """Generates HTML links to team pages with caching"""
    
    def __init__(self, server, database):
        self.conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
        self._cache_hits = 0
        self._cache_misses = 0
        
    @lru_cache(maxsize=2000)
    def get_team_data(self, team_id):
        """
        Cached lookup for team page status
        
        Returns: (Has_Page, Page_URL, Slug, Status)
        """
        self._cache_misses += 1
        
        try:
            with pyodbc.connect(self.conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        Has_Team_Page, 
                        Team_Page_URL, 
                        Team_Slug,
                        Team_Page_Status
                    FROM HS_Team_Names 
                    WHERE ID = ?
                """, team_id)
                
                row = cursor.fetchone()
                if row:
                    return (
                        bool(row.Has_Team_Page),
                        row.Team_Page_URL,
                        row.Team_Slug,
                        row.Team_Page_Status or 'None'
                    )
                return (False, None, None, 'None')
                
        except Exception as e:
            logger.error(f"Error checking team page for ID {team_id}: {e}")
            return (False, None, None, 'None')
    
    def generate_link(self, team_id, team_name, link_type='icon', css_class='team-link'):
        """
        Generate HTML link based on page availability
        
        Args:
            team_id: ID from HS_Team_Names
            team_name: Display name of team
            link_type: 'icon' | 'full' | 'both'
            css_class: CSS class for link
        
        Returns:
            HTML string
        """
        has_page, url, slug, status = self.get_team_data(team_id)
        
        # Icon definitions (using FontAwesome classes)
        icon_html = '<i class="fas fa-external-link-alt"></i>'
        
        # Generate link if page is published
        if has_page and url and status == 'Published':
            if link_type == 'icon':
                return f'<a href="{url}" class="{css_class} icon-only" title="View {team_name} team page" target="_blank">{icon_html}</a>'
            elif link_type == 'full':
                return f'<a href="{url}" class="{css_class}" target="_blank">{team_name}</a>'
            elif link_type == 'both':
                return f'<a href="{url}" class="{css_class}" target="_blank">{team_name} <span class="link-icon">{icon_html}</span></a>'
        
        # Handle draft pages (show different icon)
        elif status == 'Draft':
            draft_icon = '<i class="fas fa-file-alt" style="color: #ffa500;"></i>'
            if link_type == 'icon':
                return f'<span class="draft-page-icon" title="Page in development">{draft_icon}</span>'
            else:
                return f'<span class="team-name-draft">{team_name}</span>'
        
        # No page available
        else:
            if link_type == 'icon':
                return f'<span class="no-page-icon" title="Page coming soon" style="color:#ddd; cursor:help;">□</span>'
            elif link_type == 'full':
                return f'<span class="team-name-no-link">{team_name}</span>'
            else:
                return team_name
    
    def get_cache_stats(self):
        """Return cache statistics for monitoring"""
        return {
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'hit_rate': self._cache_hits / (self._cache_hits + self._cache_misses) if (self._cache_hits + self._cache_misses) > 0 else 0
        }
    
    def clear_cache(self):
        """Clear the LRU cache (use after bulk updates)"""
        self.get_team_data.cache_clear()
        self._cache_hits = 0
        self._cache_misses = 0


# Singleton pattern for easy import across all generators
_instance = None

def get_link_generator(server, database):
    """
    Get the global TeamLinkGenerator instance
    
    Usage:
        linker = get_link_generator('SERVER', 'DATABASE')
    """
    global _instance
    if _instance is None:
        _instance = TeamLinkGenerator(server, database)
        logger.info("TeamLinkGenerator initialized")
    return _instance


def generate_slug_for_team(team_id, server, database):
    """
    Utility function to generate and save slug for a team
    
    Usage:
        generate_slug_for_team(12345, 'SERVER', 'DATABASE')
    """
    try:
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
        
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            
            # Get team info
            cursor.execute("""
                SELECT Team_Name, City, State 
                FROM HS_Team_Names 
                WHERE ID = ?
            """, team_id)
            
            row = cursor.fetchone()
            if not row:
                logger.error(f"Team ID {team_id} not found")
                return None
            
            team_name, city, state = row
            
            # Generate slug
            slug = SlugGenerator.create(state, city, team_name)
            
            # Generate URL
            url = f"/static-football-rankings/pages/teams/{state.lower()}/{slug}/index.html"
            
            # Update database
            cursor.execute("""
                UPDATE HS_Team_Names
                SET Team_Slug = ?,
                    Team_Page_URL = ?
                WHERE ID = ?
            """, slug, url, team_id)
            
            conn.commit()
            
            logger.info(f"Generated slug for {team_name}: {slug}")
            return slug
            
    except Exception as e:
        logger.error(f"Error generating slug for team {team_id}: {e}")
        return None


# Example usage
if __name__ == "__main__":
    # Test slug generation
    print("=== Testing Slug Generator ===")
    print(f"WA, Everett, Seagulls → {SlugGenerator.create('WA', 'Everett', 'Seagulls')}")
    print(f"Everett (WA) → {SlugGenerator.create_from_team_name('Everett (WA)')}")
    print(f"TX, Allen, Eagles → {SlugGenerator.create('TX', 'Allen', 'Eagles')}")
    print(f"Fort Lauderdale St. Thomas Aquinas (FL) → {SlugGenerator.create_from_team_name('Fort Lauderdale St. Thomas Aquinas (FL)')}")