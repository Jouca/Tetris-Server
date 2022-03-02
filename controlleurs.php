<?php
$page = "mailss";

if (isset($_POST["ml"]) && isset($_POST["pr"]) && isset($_POST["ms"]) && $_POST["ml"] != "" && $_POST["pr"] != "" && $_POST["ms"] != "") {
  //envoi d'un e-mail pour inscription
  // ml = mail
  // pr = prenom
  // ms = message
  $to= 'noreply@tetrisnsi.tk';
  $sujet = 'Vérification Email Tetris';
  $fromMail = $_POST["ml"];
  $fromName = $_POST["pr"];
  $message = $_POST["ms"];
  $entete = 'From: tetris-nsi@noreply.com';
  $entete.= 'Return-Path: tetris-nsi@noreply.com';
  $entete.= 'MIME-Version: 1.0'.'\n';
  $entete.= 'Content-Type: text/html; charset=UTF=8\r\n';
  $entete.= 'X-Mailer: PHP/' . phpversion();

  //fonction e-mail
  require_once("mailer/PHPMailer.php");
  require_once("mailer/SMTP.php");
  require_once("mailer/OAuth.php");
  require_once("mailer/POP3.php");
  require_once("mailer/Exception.php");
  $mail = new PHPMailer\PHPMailer\PHPMailer();
  $mail->IsSMTP();
  $mail->SMTPDebug=0;
  $mail->SMTPAuth=true;
  $mail->SMTPSecure='ssl';
  $mail->Host='smtp.ionos.fr';
  $mail->Port=465;
  $mail->Username='owner@hexatm.com';
  $mail->Password='99P@rcourSup;';
  //die($to.$fromMail);
  $mail->setFrom($to);
  $mail->AddAddress($fromMail);
  $mail->mime_content_type = "text/html";
  $mail->CharSet = "utf-8";
  $mail->Subject = $sujet;
  $mail->msgHTML(sprintf('<html><body>%s<body><html>', $message));
  $mail->IsHTML(true);

  if (!$mail->Send()){
      die("Mailer Error: " . $mail->ErrorInfo);
      //echo 'Mailer error:'.$mail->Errorinfo;
  } else {
      die($to.$fromMail);
  }
//fin fonction e-mail
} else {
  die("Erreur dans l'envoi du mail");
}
?>
