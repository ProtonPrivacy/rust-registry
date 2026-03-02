---
layout: default
---

{% comment %}Liquid syntax cheat sheet : https://www.fabriziomusacchio.com/blog/2021-08-12-Liquid_Cheat_Sheet/{% endcomment %}

## How-To use the registry

{% include 404.html %}

## Registered Packages

{% for pkg in site.data.packages_info.packages %}
<table class="styled-table">    
    <tr>
        <td class="name">
            <a href="{{ pkg.readme }}">{{ pkg.name }}</a>
        </td>
        <td class="version">
            {{ pkg.version }}
        </td>
        <td class="prev-versions">
            {% if pkg.prev-versions %}
            {% if pkg.prev-versions.size > 3 %}
            <button type="button" class="collapsible" onclick="onClickCollapsible(this)">Prev. Versions: {{pkg.prev-versions[0]}} / ... ({{pkg.prev-versions.size| minus: 2}} more) ... / {{pkg.prev-versions[-1]}} (click to expand)</button>
             <div class="collapsible-content">
               <p>{{ pkg.prev-versions | join: " / " }}</p>
             </div>
            {% else %}
            Prev. Versions: {{ pkg.prev-versions | join: " / " }}
            {% endif %}
            {% else %}
            Prev. Versions: [no]
            {% endif %}
        </td>
    </tr>
    <tr>
        <td colspan="3" class="description">
            Description: {{ pkg.description }}
        </td>
    </tr>
    <tr>
        <td colspan="3" class="authors">
            Authors: {{ pkg.authors }}
        </td>
    </tr>
    <tr>
        <td colspan="3" class="keywords">
            Keywords: {{ pkg.keywords }}
        </td>
    </tr>
    <tr>
        <td colspan="3" class="categories">
            Categories: {{ pkg.categories }}
        </td>
    </tr>
</table>
{% endfor %}
