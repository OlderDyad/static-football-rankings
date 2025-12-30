# generate_national_champions.py
def generate_nc_json(source_type='media'):
    """Generate NC JSON for media or mcknight"""
    
    # Call unified stored procedure
    cursor.execute("EXEC sp_Get_National_Champions @SourceType=?", source_type)
    
    # Build standardized JSON
    items = []
    for row in cursor.fetchall():
        # Generate link HTML
        if row.hasProgramPage and row.programPageUrl:
            linkHtml = f'<a href="{row.programPageUrl}">🔗</a>'
        else:
            linkHtml = '□'
        
        items.append({
            'year': row.year,
            'team': row.team,
            'state': row.state,
            'record': row.record,
            'combined': float(row.combined) if row.combined else 0,
            # ... all other fields
            'teamLinkHtml': linkHtml
        })
    
    # Standardized structure
    output = {
        'metadata': {
            'type': 'national-champions',
            'source': source_type,
            'timestamp': datetime.now().isoformat(),
            'totalItems': len(items)
        },
        'items': items
    }
    
    # Write to correct location
    output_path = f'docs/data/{source_type}-national-champions/{source_type}-national-champions.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

# Generate both
generate_nc_json('media')
generate_nc_json('mcknight')