CREATE TABLE `file_deletions` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `file_id` bigint(20) unsigned NOT NULL,
  `site_id` int(10) unsigned NOT NULL,
  `exitcode` smallint(5) NOT NULL,
  `batch_id` bigint(20) unsigned NOT NULL,
  `created` datetime NOT NULL,
  `started` datetime NOT DEFAULT NULL,
  `finished` datetime NOT DEFAULT NULL,
  `completed` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `deletion` (`file_id`,`site_id`),
  KEY `batch` (`batch_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1 COLLATE=latin1_general_cs;
