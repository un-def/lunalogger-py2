DROP TABLE IF EXISTS `chat`;
CREATE TABLE `chat` (
  `message_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `time` int(10) unsigned NOT NULL,
  `user` int(10) unsigned NOT NULL,
  `message` text NOT NULL,
  `me` tinyint(1) unsigned NOT NULL,
  PRIMARY KEY (`message_id`),
  KEY `user` (`user`),
  KEY `time` (`time`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `user_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `nick` varchar(32) NOT NULL,
  `message_count` int(10) unsigned NOT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `nick` (`nick`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
