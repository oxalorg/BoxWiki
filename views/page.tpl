% rebase('base.tpl')
<h1>{{ title }}</h1>
<article>
{{ !content }}
</article>
<div class="attachments">
<ul>
% for item in attachments:
<li><a href="{{ item }}">{{ item }}</a></li>
% end
</ul>

