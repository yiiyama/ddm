<?php

include('/var/www/cgi-bin/dynamo/common/communicator.php');

$filename=$_FILES['file']['name'];
$filedata = $_FILES['file']['tmp_name'];
$email = $email=$_POST['email'];


if ($_FILES['file']['error'] > 0)
  {
    echo "Error: " . $_FILES['file']['error'] . "<br>";
  }
elseif ( end(explode('.', $filename)) != "txt" )
  {
    echo "<div style ='font:20px/21px Arial,tahoma,sans-serif;color:#000000'> Error: file $filename does not have the correct type.</div>" . "<br>";
    echo "<div style ='font:20px/21px Arial,tahoma,sans-serif;color:#000000'> It has to be a .txt file.</div>" . "<br>";
  }
else
  {
    $username=$_REQUEST['user'];

    $userid = check_authentication($username,$db);
    $hash = hash_file('md5',$filedata);
    $rand = rand(1,10000000);

    while (is_dir($uploadpath.$hash.$rand)){
      $rand = rand(1,10000000);
    }

    if (!filecopy($filedata,$uploadpath.$hash.$rand."/policystack.txt")){
      if (filecopy("/var/www/html/dynamo/dynamo/dummy_exec.py",$uploadpath.$hash.$rand."/exec.py"))
	echo "Something went wrong with copying the detox executable";

      if(!$email){
	$qstring ="SELECT u.`email` FROM users AS u INNER JOIN authorized_users as au WHERE lower(u.`name`) = lower('$username') AND u.`id` = au.`user_id`";
	if (!execQuery($qstring,$db)){
	  echo "Not a valid user."; echo "\n";
	  exit();
	}
	else{
	  $email = execQuery($qstring,$db);
	}
      }

      communicate(0,"DeletionCampaign",$hash.$rand,$db,$userid,$email,"--policy policstack.txt");
      echo "Results will be sent to you shortly."; echo "\n";
    }
    else{
      echo "Something went wrong."; echo "\n";
    }
  }
?>
