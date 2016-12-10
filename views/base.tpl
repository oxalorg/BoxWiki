<html>
<head>
    <title>{{title or 'BoxWiki'}}</title>
    <link rel="stylesheet" type="text/css" href="/static/css/main.css">
    <script>
    function addSlashToUrl() {
        //If there is no trailing shash after the path in the url add it
        if (window.location.pathname.endsWith('/') === false) {
            var url = window.location.protocol + '//' + 
                    window.location.host + 
                    window.location.pathname + '/' + 
                    window.location.search;

            window.history.replaceState(null, document.title, url);
        }
    }
    window.onload = function () {
        addSlashToUrl()
    };
    </script>
</head>
<body>
<div class="container">
<div class="row">
<div id="side" class="column">
<ul>
    <li><a href="/">index</a></li>
    <li><a href="/wiki">wiki</a></li>
    <li><a href="/add">add page</a></li>
</ul>
</div>
<div id=main class="column column-75">
  {{!base}}
</div>
</div>
</body>
</html>
