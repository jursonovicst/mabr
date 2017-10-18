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
        width: <?php echo array_key_exists('width', $query) ? $query['width'] : 630?>px;
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
<?php
foreach($query as $key => $value){
  if ($key=="width") {
    continue;
  }
?>
      <tr>
        <td>
<?php
echo "<a href=\"" . $value . "\">".$key."</a>\n";
?>
        </td>
      </tr>
      <tr>
        <td>
<?php
echo "<div> <video data-dashjs-player autoplay muted src=\"".$value."\" controls></video> </div>\n"
?>
        </td>
      </tr>
<?php
}
?>
    </table>

</BODY>
</HTML>

