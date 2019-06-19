# systemd configs

You can run COBalD as a system service.
We provide to configs for a single COBalD instance and a multi COBalD instance setup.
For both setups you have to modify: 

 - Please modify the file by changing the `WorkingDirectory` to where your COBalD config is.
 - You have to copy one of the `*.service` into the `/usr/lib/systemd/system` directory.
 - You need to run `systemctl daemon-reload` after you copied or changed the file.
 
Which of these files you have to copy, depends on how many COBalD instances you want to run.

## Single COBalD Instance:
Copy the file `cobald.service` into the `/usr/lib/systemd/system` directory.

 - `systemctl start cobald` starts one instance of COBalD as a service
 - `systemctl stop cobald` stops the instance of COBald
 - `systemctl status cobald` reports the current status of the COBalD instance
 - `systemctl enable cobald` the COBalD instance starts at system boot
 
 ## Multiple COBalD Instances:
Copy the file `cobald@.service` into the `/usr/lib/systemd/system` directory.
You can manage several instances which are identified with a systemd instance name.
The COBalD instance loads the `cobald_instance.yaml` config in the `WorkingDirectory`.

 - `systemctl start cobald@instance` starts one instance of COBalD as a service with the configuration file
    `cobald_instance.yaml` 
 - `systemctl stop cobald@instance` stops the instance of COBald with the configuration file `cobald_instance.yaml` 
 - `systemctl status cobald@instance` reports the current status of the COBalD instance with the configuration file
    `cobald_instance.yaml` 
 - `systemctl enable cobald@instance` COBalD instance starts at system boot with the configuration file
    `cobald_instance.yaml` 