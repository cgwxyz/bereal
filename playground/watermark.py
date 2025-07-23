## coding=utf-8

import os
import time
from datetime import datetime
import json
from io import BytesIO
import logging

from PIL import Image, ImageDraw, ImageFont, ImageFile
import pytz

from baseopensdk import BaseClient
from baseopensdk.api.base.v1 import *
from baseopensdk.api.drive.v1 import *

ImageFile.LOAD_TRUNCATED_IMAGES = True

_LOGGER = logging.getLogger(__name__)

BASE_PATH = os.path.abspath(os.path.dirname(__file__))

_FONT_BOLD_PATH = BASE_PATH + '/fonts/SourceHanSansOLD-Bold-2.otf'
_FONT_PATH = BASE_PATH + "/fonts/SourceHanSansSC-Regular-2.otf"

WEEKS = [u'星期日', u'星期一', u'星期二', u'星期三', u'星期四', u'星期五', u'星期六']
_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def convert_to_cst_time(external_time):
  # 获取当前时区
  current_timezone = datetime.now(pytz.timezone('UTC')).astimezone().tzinfo
  # 将外部传入的时间转换为datetime对象
  dt = datetime.strptime(external_time, "%Y-%m-%d %H:%M:%S")

  # 获取外部传入时间的时区
  external_timezone = dt.replace(tzinfo=current_timezone)

  # 将外部传入的时间转换为北京时间
  cst_timezone = pytz.timezone('Asia/Shanghai')
  cst_time = external_timezone.astimezone(cst_timezone)
  weekday = cst_time.strftime("%w")
  return cst_time.strftime('%Y-%m-%d'), cst_time.strftime('%H:%M'), WEEKS[int(
      weekday)]


def stamp2time(stamp, _format=_TIME_FORMAT):
  time_tuple = time.localtime(stamp)
  return time.strftime(_format, time_tuple)


def add_color_bar(height, width=6, color=(24, 144, 255)):
  tmp_img = Image.new("RGBA", (width, height), color)
  return tmp_img


def download_attach(client, table_id, record_id, field_id, file_token):
  # 高级权限鉴权信息 文档未开启高级权限则无需传 extra 字段
  extra = json.dumps({
      "bitablePerm": {
          "tableId": table_id,  # 附件所在数据表 id
          "attachments": {
              field_id: {  # 附件字段 id
                  record_id: [  # 附件所在记录 record_id
                      file_token  # 附件 file_token
                  ]
              }
          }
      }
  })
  # 构造请求对象
  request = DownloadMediaRequest.builder() \
      .file_token(file_token) \
      .extra(extra) \
      .build()
  # 发起请求
  response = client.drive.v1.media.download(request)
  return response.file.read()


def jpeg2png(source_img):
  source_im = Image.open(source_img)
  if source_im.mode != 'RGBA':
    tmp_im = source_im.convert("RGBA")
    return tmp_im
  return source_im


def add_text(content,
             fnt,
             color="black",
             backgroundcolor=(38, 38, 38, 0),
             background_fixed_width=1,
             background_img=None,
             fixed_width=0,
             paddingleft=0,
             paddingtop=0,
             wrap_align_mode=0,
             max_char=15,
             multi_line=False,
             max_width=0,
             header="",
             height=40):
  """

    :param content:  文字内容
    :param fnt: 字体
    :param color: 文字颜色
    :param backgroundcolor:  背景色
    :param background_fixed_width: 背景固定宽度
    :param paddingleft: 左边向右偏移距离
    :param paddingtop: 距离顶部间距
    :param wrap_align_mode:  0左对齐, 1第2行偏移字段名长度
    :param max_char: 单行最多字符数
    :param multi_line: 允许多行，如不允许，超出一行部分替换为"..." ，配合max_char使用
    :param max_width: 单行最大宽度，超出自动换行
    :param header: 字段名文字内容，配合wrap_align_mode 对齐使用
    :param height: 行高
    :return:
    """
  # 获取文字实际长度
  content = content or u""
  tmp_img = Image.new("RGBA", (400, height + paddingtop), (0, 0, 0, 0))
  tmp_draw = ImageDraw.Draw(tmp_img)
  bbox = tmp_draw.textbbox((0, 0), content, font=fnt)
  real_width = bbox[2] - bbox[0]
  real_height = bbox[3] - bbox[1] + 10
  fixed_width = real_width + paddingleft + 10 if fixed_width == 0 else fixed_width
  max_width = fixed_width if max_width == 0 else max_width  # 单行最大宽度
  max_width -= paddingleft * 2
  # 检查是否需要换行
  if real_width > max_width > 0 and multi_line:  # need break
    # 头宽度,字段对应内容换行
    header_w = 0  # 左对齐
    if wrap_align_mode:
      tmp_box = tmp_draw.textbbox((0, 0), header, font=fnt) if header else 0
      header_w = int(tmp_box[2] - tmp_box[0])
    lines = []
    tmp_line = []
    char_count = len(content)
    idx = 0
    whole_line_width = 0
    while idx < char_count:
      tmp_bbox = tmp_draw.textbbox((0, 0), content[idx], font=fnt)
      tmp_w = tmp_bbox[2] - tmp_bbox[0]
      if whole_line_width + tmp_w > max_width:  # 超过最大宽度，需要换行
        lines.append(''.join(tmp_line))
        tmp_line = [content[idx]]  # 重新初始化
        whole_line_width = tmp_w + header_w  # 初始化宽度
      else:
        whole_line_width += tmp_w
        tmp_line.append(content[idx])
      idx += 1
    lines.append(''.join(tmp_line))
    real_width = fixed_width if background_fixed_width == 1 else real_width + paddingleft
    text_img = Image.new(
        "RGBA", (real_width, real_height * len(lines) + 10 + paddingtop),
        backgroundcolor) if background_img is None else background_img
    for idx, line in enumerate(lines):
      draw = ImageDraw.Draw(text_img)
      text_position = (paddingleft if idx == 0 else header_w + paddingleft,
                       idx * real_height + paddingtop)
      draw.text(text_position, line, color, font=fnt)
    return text_img, real_height * len(lines) + paddingtop, real_width
  else:
    real_width = fixed_width if background_fixed_width == 1 else real_width + paddingleft
    text_img = Image.new(
        "RGBA", (real_width, real_height + 10 + paddingtop),
        backgroundcolor) if background_img is None else background_img
    draw = ImageDraw.Draw(text_img)
    text_position = (paddingleft, paddingtop)
    # 文本位置, 颜色, 透明度
    if not multi_line:
      content = content if len(
          content) <= max_char else content[0:max_char] + '...'
    draw.text(text_position, content, color, font=fnt)
  return text_img, real_height + paddingtop, real_width


def gen_watermark(personal_token, app_token, table_id, record_id,
                  t_submit_field, source_field, target_field, location_field):
  # 构建client
  client: BaseClient = BaseClient.builder() \
      .app_token(app_token) \
      .personal_base_token(personal_token) \
      .build()

  # 2. 获取当前表字段信息
  list_field_request = ListAppTableFieldRequest.builder() \
  .page_size(100) \
  .table_id(table_id) \
  .build()

  list_field_response = client.base.v1.app_table_field.list(list_field_request)
  return_code = getattr(list_field_response, 'code', '')
  if return_code != 0:
    print('get code:', return_code)
    return

  fields = getattr(list_field_response.data, 'items', [])
  field_map = {}
  for field in fields:
    field_map.update({field.field_id: field.field_name})

  # 获取指定记录
  get_record_req = GetAppTableRecordRequest.builder().table_id(
      table_id).record_id(record_id).build()
  get_record_response = client.base.v1.app_table_record.get(get_record_req)
  record = getattr(get_record_response.data, 'record', {})
  fields = getattr(record, 'fields', {})

  #地理位置
  location = fields.get(field_map.get(location_field))
  location = location or {}

  # 附件
  source_attaches = fields.get(field_map.get(source_field))

  # 提交时间
  t_submit = int(fields.get(field_map.get(t_submit_field)) / 1000)

  # 下载附件
  new_file_tokens = []
  for attach in source_attaches:
    if attach.get('type') not in ['image/jpeg', 'image/png']:
      # 只处理图片
      continue
    attach_body = download_attach(client, table_id, record_id, source_field,
                                  attach.get('file_token', ''))
    params = []
    if location.get('full_address', ''):
      params.append({
          'field_key': 10,
          "field_value": location.get('full_address', '未获取到地址')
      })
    if location.get('location', ''):
      longitude, latitude = location.get('location', '').split(',')
      longitude = '%s%s' % (abs(
          float(longitude)), u'°E' if float(longitude) > 0 else u'°W')
      latitude = '%s%s' % (abs(
          float(latitude)), u'°N' if float(latitude) > 0 else u'°S')
      params.append({
          'field_key': "11",
          "field_value": "经纬度: %s, %s" % (longitude, latitude)
      })
    params.reverse()

    t_submit_date, t_submit_time, t_submit_week = convert_to_cst_time(
        stamp2time(t_submit))

    watermark_img_mem_file = add_team_watermark_v1(attach_body, t_submit_time,
                                                   t_submit_date,
                                                   t_submit_week, params)
    _LOGGER.info("goto upload")
    # 上传附件
    watermark_img = watermark_img_mem_file.read()
    upload_request = UploadAllMediaRequest.builder() \
                        .request_body(UploadAllMediaRequestBody.builder()
                            .file_name("%s.jpg" % int(time.time()))
                            .parent_type("bitable_file")
                            .parent_node(app_token)
                            .size(len(watermark_img))
                            .file(watermark_img)
                            .build()) \
                        .build()
    # 发起请求
    response: UploadAllMediaResponse = client.drive.v1.media.upload_all(
        upload_request)
    file_token = getattr(response.data, 'file_token', '')
    if file_token:
      new_file_tokens.append(file_token)

  _LOGGER.info('get new_file_tokens:%s', new_file_tokens)
  if new_file_tokens:
    # 添加到指定字段
    request = UpdateAppTableRecordRequest.builder() \
                .table_id(table_id) \
                .record_id(record_id) \
                .request_body(AppTableRecord.builder()
                        .fields({
                            field_map.get(target_field): [{"file_token": file_token} for file_token in new_file_tokens]
                        })
                        .build()) \
                .build()

    # 发起请求
    response: UpdateAppTableRecordResponse = client.base.v1.app_table_record.update(
        request)
    _LOGGER.info("done")
  return


def add_team_watermark_v1(source_img_data, curr_time, curr_date, curr_week_day,
                          params):
  im1 = jpeg2png(BytesIO(source_img_data))
  width1, height1 = im1.size
  max_width = width1
  # 获取布局
  layout_setting = {
      'left': 20,
      "params_gap": {
          'left': 40,
          'right': 20
      },
      'show_area': {
          'size': 32,
          'backgroundcolor': (38, 38, 38, 0),
          'fixed_width': 0,
          'paddingleft': 0
      },
      'time': {
          'size': 100,
          'left': 0,
          'top': 23,
          'color': "white"
      },
      'date': {
          'size': 32,
          'left': 30,
          'top': 25,
          'color': "white"
      },
      'week': {
          'size': 32,
          'left': 30,
          'top': 75,
          'color': "white"
      },
      'poweredby': {
          'size': 30,
          'left': 30,
          'top': 75,
          'color': "white"
      },
      'normal_size': 32,
      'split_bar': {
          'visible': 1,
          'color': (255, 204, 0, 255),
          'width': 4,
          'paddingtop': 0,
          'paddingleft': 10
      },
      'address_gap': {
          'left': 40,
          'top': 160
      },
      'date_gap': {
          'left': 40,
          'top': 250
      },
      'max_char': 18,
  }

  gap = layout_setting.get('params_gap', {}).get('left', 10)
  top_checkin_h = 120
  # 创建新图层 2倍LOGO
  layer = Image.new("RGBA", im1.size, (255, 255, 255, 0))

  # 从最后一层
  text_left_gap = gap
  exist_dot = 0
  params_height = 0
  banner_text = ''
  if params is not None:
    line_gap = layout_setting.get('show_area', {}).get('linegap', 5)
    for idx, item in enumerate(params):
      fnt = ImageFont.truetype(
          _FONT_PATH,
          layout_setting.get('show_area', {}).get('size', 30))
      max_width = width1 - text_left_gap - layout_setting.get(
          'params_gap', {}).get('right', 30)

      if item.get('field_name'):
        content = u'%s：%s' % (item.get('field_name'), item.get('field_value'))
      else:
        content = item.get('field_value', '')

      text_img, tmp_height, _ = add_text(
          content,
          fnt,
          color="white",
          multi_line=True,
          background_fixed_width=layout_setting.get('show_area',
                                                    {}).get('fixed_width', 0),
          backgroundcolor=layout_setting.get('show_area',
                                             {}).get('backgroundcolor'),
          max_width=max_width * 2 / 3,  # 显示最大宽度，超过换行
          fixed_width=max_width,
          paddingleft=layout_setting.get('show_area',
                                         {}).get('paddingleft', 0),
          paddingtop=layout_setting.get('show_area', {}).get('paddingtop', 0),
          header=u'%s：' % item.get('field_name'),
          max_char=layout_setting.get('show_area', {}).get('max_char', 0))
      params_height += tmp_height + line_gap

      layer.paste(text_img,
                  (text_left_gap + 10 if exist_dot else text_left_gap,
                   int(height1 - params_height - 20)))  # left top

  # 添加打卡时间点
  fnt = ImageFont.truetype(_FONT_BOLD_PATH,
                           layout_setting.get('time', {}).get('size',
                                                              30))  # font,
  text_img, time_height, time_width = add_text(curr_time,
                                               fnt,
                                               color=layout_setting.get(
                                                   'time',
                                                   {}).get('color', 'white'),
                                               background_fixed_width=0,
                                               backgroundcolor=(38, 38, 38, 0))
  layer.paste(text_img,
              (int(gap + layout_setting.get('time', {}).get('left', 0)),
               int(height1 - params_height - top_checkin_h - 40 +
                   layout_setting.get('time', {}).get('top', 0))))

  # 添加分隔条
  bar = add_color_bar(time_height,
                      width=layout_setting.get('split_bar', {}).get('width'),
                      color=layout_setting.get('split_bar', {}).get('color'))
  layer.paste(bar, (gap + time_width +
                    layout_setting.get('split_bar', {}).get('paddingleft', 0),
                    int(height1 - params_height - top_checkin_h - 30 +
                        layout_setting.get('time', {}).get('top', 0))))

  # 添加日期 和星期
  fnt = ImageFont.truetype(_FONT_PATH,
                           layout_setting.get('date', {}).get('size',
                                                              30))  # font,
  text_img, _, _ = add_text(curr_date,
                            fnt,
                            color=layout_setting.get('date',
                                                     {}).get('color', 'white'),
                            background_fixed_width=0,
                            backgroundcolor=(38, 38, 38, 0),
                            height=40)
  layer.paste(
      text_img,
      (int(gap + time_width + layout_setting.get('date', {}).get('left', 0)),
       int(height1 - params_height - top_checkin_h - 40 +
           layout_setting.get('date', {}).get('top', 0))))

  # 添加星期
  fnt = ImageFont.truetype(_FONT_PATH,
                           layout_setting.get('week', {}).get('size',
                                                              30))  # font,
  text_img, _, _ = add_text(curr_week_day,
                            fnt,
                            color=layout_setting.get('week',
                                                     {}).get('color', 'white'),
                            background_fixed_width=0,
                            backgroundcolor=(38, 38, 38, 0),
                            height=40)
  layer.paste(
      text_img,
      (int(gap + time_width + layout_setting.get('date', {}).get('left', 0)),
       int(height1 - params_height - top_checkin_h - 40 +
           layout_setting.get('week', {}).get('top', 0))))
  # add powerdby
  fnt = ImageFont.truetype(_FONT_PATH,
                           layout_setting.get('poweredby',
                                              {}).get('size', 30))  # font,
  text_img, text_height, text_width = add_text("PoweredBy\n水印快拍",
                                               fnt,
                                               color=layout_setting.get(
                                                   'poweredby',
                                                   {}).get('color', 'white'),
                                               background_fixed_width=0,
                                               backgroundcolor=(38, 38, 38, 0),
                                               height=40)
  layer.paste(text_img,
              (int(width1 - text_width - 20), int(height1 - text_height - 20)))

  out = Image.composite(layer, im1, layer)
  out = out.convert('RGB')
  out_mem = BytesIO()
  out.save(out_mem, 'JPEG', quality=95)
  out_mem.seek(0)
  return out_mem
