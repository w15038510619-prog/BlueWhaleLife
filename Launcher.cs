using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace BlueWhaleLife
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            string targetExe = Path.Combine(baseDir, "dist", "BlueWhaleLife", "BlueWhaleLife.exe");

            if (!File.Exists(targetExe))
            {
                MessageBox.Show(
                    "未找到核心运行程序：\n" + targetExe + "\n\n请确认 dist/BlueWhaleLife 文件夹存在。",
                    "大肥鱼的B站生活",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning
                );
                return;
            }

            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = targetExe;
            psi.WorkingDirectory = baseDir;
            if (args != null && args.Length > 0)
            {
                psi.Arguments = string.Join(" ", args);
            }
            psi.UseShellExecute = false;

            try
            {
                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show("启动大肥鱼失败: " + ex.Message, "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
