<!DOCTYPE html PUBLIC "-//IETF//DTD HTML 2.0//EN">
<?php
parse_str($_SERVER['QUERY_STRING'],$query);
?>
<HTML>
   <HEAD>
      <TITLE>
         mABR test dite
      </TITLE>
    <script src="http://cdn.dashjs.org/latest/dash.all.min.js"></script>
    <style>
      video {
        width: <?php echo array_key_exists('width', $query) ? $query['width'] : 640?>px;
      }
    </style>

   </HEAD>
<BODY>
<a href="https://time.is/Velbert" id="time_is_link" rel="nofollow" style="font-size:36px">Wall clock time:</a>
<span id="Velbert_z704" style="font-size:36px"></span>
<script src="//widget.time.is/t.js"></script>
<script>
time_is_widget.init({Velbert_z704:{}});
</script>

<table cellspacing="0" cellpadding="0">
      <tr>
<?php
foreach($query as $key => $value){
    if ($key=="width") {
        continue;
    }
    echo "<td>".$key."</td>\n";
}
?>
      </tr>
      <tr>
<?php
parse_str($_SERVER['QUERY_STRING'],$query);
foreach($query as $key => $value){
    if ($key=="width") {
        continue;
    }
    echo "<td><a href=\"" . $value . "\">".$key."</a></td>\n";
}
  #      <td><a href="http://mabr-origin.la.t-online.de/mabr/ch02/ch02.mpd">ch02</a></td>
?>
      </tr>
      <tr>
<?php
foreach($query as $key => $value){
    if ($key=="width") {
        continue;
    }

?>
        <td>
<?php
echo "<div> <video data-dashjs-player autoplay muted src=\"".$value."\" controls></video> </div>\n"
?>
        </td>
<?php
}
?>
      </tr>
    </table>

</BODY>
</HTML>

