#include "common.h"

void dc_atk_8266_msg_show(u16 x,u16 y,u8 wanip)
{
	u8 *p,*p1,*p2;
	p=mymalloc(32);							//����32�ֽ��ڴ�
	p1=mymalloc(32);							//����32�ֽ��ڴ�
	p2=mymalloc(32);							//����32�ֽ��ڴ�
	Lcd_Clear(WHITE);
	POINT_COLOR=BLUE;

	if(wanip==0)//ȫ����
	{
		p=atk_8266_check_cmd("SDK version:");
		p1=(u8*)strstr((const char*)(p+12),"(");
		*p1=0;
		Show_Str(x,y,128,16,"Version:",12,0);	Show_Str(x+8*6,y,128,16,p+12,12,0);
		atk_8266_send_cmd("AT+CWMODE?","+CWMODE:",20);	//��ȡ����ģʽ
		p=atk_8266_check_cmd(":");
		Show_Str(x,y+16,128,16,"Mode:",12,0);Show_Str(x+6*5,y+16,128,16,(u8*)ATK_ESP8266_CWMODE_TBL[*(p+1)-'1'],12,0);
  	    atk_8266_send_cmd("AT+CWSAP?","+CWSAP:",20);	//��ȡwifi����
		p=atk_8266_check_cmd("\"");
		p1=(u8*)strstr((const char*)(p+1),"\"");
		p2=p1;
		*p1=0;
		Show_Str(x,y+32,128,16,"SSID:",12,0);Show_Str(x+6*5,y+32,128,16,p+1,12,0);
		p=(u8*)strstr((const char*)(p2+1),"\"");
		p1=(u8*)strstr((const char*)(p+1),"\"");
		p2=p1;
		*p1=0;		
		Show_Str(x,y+48,128,16,"mima:",12,0);Show_Str(x+6*5,y+48,128,16,p+1,12,0);
		p=(u8*)strstr((const char*)(p2+1),",");
		p1=(u8*)strstr((const char*)(p+1),",");
		*p1=0;
		Show_Str(x,y+64,128,16,"Honel:",12,0);Show_Str(x+6*6,y+64,128,16,p+1,12,0);
		Show_Str(x,y+80,128,16,"FShi:",12,0);Show_Str(x+6*5,y+80,128,16,(u8*)ATK_ESP8266_ECN_TBL[*(p1+1)-'0'],12,0);
	}
	myfree(p);		//�ͷ��ڴ� 
	myfree(p1);		//�ͷ��ڴ� 
	myfree(p2);		//�ͷ��ڴ� 
}

long long sys_tick=0;  
uint32_t g_connect=0;	//����ģʽ
uint32_t g_clean = 0;

u8 atk_8266_wifiap_test(void)
{
	u8 key;
	u8 timex=0; 
	u8 ipbuf[16]; 	//IP����
	u8 *p,*prc,*name=0;
	u16 t=999;		//���ٵ�һ�λ�ȡ����״̬
	u8 res=0;
	u16 rlen=0;
	u8 constate=0;	//����״̬

	p=mymalloc(32);							//����32�ֽ��ڴ�
	prc=mymalloc(32);
	Lcd_Clear(WHITE);
	POINT_COLOR=RED;

	Show_Str(10,5,128,16,"WIFI-AP_Mode",16,0);
	Show_Str(10,30,128,16,"Config ESP...",12,0);
	atk_8266_msg_show(5,20,1);
	Lcd_Clear(WHITE);
	POINT_COLOR=RED;

	atk_8266_send_cmd("AT+CIPMUX=1","OK",20);   //0�������ӣ�1��������
	sprintf((char*)p,"AT+CIPSERVER=1,%s",(u8*)portnum);
	atk_8266_send_cmd(p,"OK",20);
	delay_ms(1000);
	Lcd_Clear(WHITE);
	POINT_COLOR=RED;

	LCD_Fill(30,50,128,50+12,WHITE);			//���֮ǰ����ʾ
	Show_Str(30,50,128,16,"Config Success!",12,0);
	delay_ms(200);
	LCD_Fill(30,80,239,80+12,WHITE);
	USART2_RX_STA=0;
	xianshi();

	while(1)
	{
	    timex=500;
	    if(timex)timex--;
	    if(timex==1)LCD_Fill(10,15,128,128,WHITE);
	    t++;
	    sys_tick++;
	    delay_ms(5);
	    prc=atk_8266_check_cmd("###");				//���յ�һ��������

	    if(strlen((char*)prc)>3)
	    {
	        printf("REC:%s",prc);	//���͵�����
		    name =strstr((const char*)prc,"unknown");

		    if(name==NULL)
		    {
		        LCD_Fill(0,59,128,128,WHITE);
				showhanzi16(10,59,4);   //
				showhanzi16(30,59,5);   //
				LCD_ShowString(50,59,88,16,16,(u8*)prc+3);
				LCD_ShowString(15,76,128,12,12,"Switch State:");
				LCD_ShowString(15,90,128,16,16,"Open");
				LED1=0;     //����
				REL = 0;
				if(!g_connect)g_connect=sys_tick;//��
			}
			else
			{
			    LCD_Fill(10,59,128,128,WHITE);
				showhanzi16(20,60,6);
				showhanzi16(40,60,7);
				showhanzi16(60,60,8);
				showhanzi16(20,90,9);
				showhanzi16(40,90,10);
				showhanzi16(60,90,11);
				showhanzi16(80,90,12);
				if(!g_clean)g_clean=sys_tick;
			}
		USART2_RX_STA=0;
		if(constate!='+')t=1000;		//״̬Ϊ��δ����,������������״̬
		else t=0;                   //״̬Ϊ�Ѿ�������,10����ټ��
		}

	    if((sys_tick-g_connect>=300)&&(g_connect!=0))
	    {
		    printf("sys_tick[%lld]g_c[%d]\r\n",sys_tick,g_connect);
		    LCD_Fill(0,76,128,128,WHITE);
		    LCD_ShowString(15,76,128,12,12,"Switch State:");
		    LCD_ShowString(15,88,128,16,16,"Close");
		    LED1=1;
		    REL =1;
		    g_connect=0;
		    if(!g_clean)g_clean=sys_tick;
	    }

	    //����5����û���յ��κ�����,��������ǲ��ǻ�����.
	    if(t%500==0)
	    {
		    constate=atk_8266_consta_check();//�õ�����״̬
		    if(constate=='+'){
			LCD_Fill(60,110,128,128,WHITE);
		    Show_Str(60,110,68,12,"Connect",12,0); } //����״̬
		else
		    {
			    LCD_Fill(60,110,128,128,WHITE);
			    Show_Str(60,110,68,12,"DisConnect",12,0);
		    }
	    }

	    if((sys_tick-g_clean>=300)&&(g_clean!=0))
	    {
		    printf("sys_tick[%lld]g_c[%d]\r\n",sys_tick,g_clean);
		    LCD_Fill(0,59,128,128,WHITE);
		    g_clean=0;
	    }

	    if((t%200)==0)LED0=!LED0;
		atk_8266_at_response(1);
	}

	myfree(p);
	myfree(prc);
	return res;
} 
